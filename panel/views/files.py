import mimetypes
from pathlib import Path

import requests as _requests
from django.conf import settings
from django.http import JsonResponse, FileResponse, StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from panel.decorators import login_required
from .helpers import (
    mimetype_for, is_voice_doc, convert_audio_to_wav,
    get_tg_file_url, can_view_user, serve_local_file,
    _WHISPER_SUPPORTED_EXT,
)
from core.models import Document, Case


@login_required
def local_file(request, filename):
    """Serve a file that was saved locally by the userbot."""
    resp = serve_local_file(filename, as_attachment=False)
    if resp is None:
        return HttpResponse("File not found", status=404)
    return resp


@login_required
def file_view(request, file_id):
    if file_id.startswith("local:"):
        filename = file_id[6:]
        resp = serve_local_file(filename, as_attachment=False)
        return resp or HttpResponse("File not found", status=404)
    url = get_tg_file_url(file_id)
    if not url:
        return HttpResponse("File not available", status=404)
    try:
        r = _requests.get(url, timeout=30, stream=True)
        ct = r.headers.get("Content-Type", "application/octet-stream")
        return StreamingHttpResponse(r.iter_content(8192), content_type=ct)
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=500)


@login_required
def file_download(request, file_id):
    download_name = request.GET.get("name", "file")
    if file_id.startswith("local:"):
        filename = file_id[6:]
        resp = serve_local_file(filename, as_attachment=True, download_name=download_name)
        return resp or HttpResponse("File not found", status=404)
    url = get_tg_file_url(file_id)
    if not url:
        return HttpResponse("File not available", status=404)
    try:
        r = _requests.get(url, timeout=30)
        from io import BytesIO
        response = FileResponse(BytesIO(r.content), as_attachment=True, filename=download_name)
        response["Content-Type"] = r.headers.get("Content-Type", "application/octet-stream")
        return response
    except Exception as e:
        return HttpResponse(f"Error: {e}", status=500)


@login_required
@require_POST
def transcribe_document(request, doc_id):
    doc = get_object_or_404(Document, pk=doc_id)
    case = doc.case
    if not can_view_user(request, case.user_id):
        return JsonResponse({"error": "Access denied"}, status=403)

    lang = (case.user.language or "").strip().lower()
    whisper_lang = lang if (len(lang) in (2, 3) and lang.isalpha()) else None

    file_id  = doc.file_id
    filename = doc.filename or "audio.oga"

    if file_id.startswith("local:"):
        path = settings.UPLOADS_DIR / Path(file_id[6:]).name
        if not path.exists():
            return JsonResponse({"error": "File not found on disk"}, status=404)
        with open(path, "rb") as f:
            data = f.read()
    else:
        url = get_tg_file_url(file_id)
        if not url:
            return JsonResponse({"error": "File URL unavailable"}, status=404)
        if not url.startswith("http"):
            url = request.build_absolute_uri(url)
        try:
            r = _requests.get(url, timeout=60)
            r.raise_for_status()
            data = r.content
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)

    if not settings.OPENAI_API_KEY:
        return JsonResponse({"error": "OpenAI API key not configured"}, status=503)

    ext = (Path(filename).suffix or "").lower()
    if ext not in _WHISPER_SUPPORTED_EXT:
        converted = convert_audio_to_wav(data, ext)
        if converted:
            data, filename = converted
        else:
            return JsonResponse(
                {"error": "Audio format not supported. Install ffmpeg on the server."},
                status=400,
            )

    whisper_data = {"model": "whisper-1"}
    if whisper_lang:
        whisper_data["language"] = whisper_lang

    try:
        import requests as req
        resp = req.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            files={"file": (filename, data, mimetype_for(filename) or "audio/wav")},
            data=whisper_data,
            timeout=60,
        )
        if not resp.ok:
            try:
                err_body = resp.json()
                err = err_body.get("error")
                msg = err.get("message", str(err)) if isinstance(err, dict) else (str(err) if err else resp.text)
            except Exception:
                msg = resp.text or f"HTTP {resp.status_code}"
            return JsonResponse({"error": msg}, status=resp.status_code)
        text = (resp.json().get("text") or "").strip()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)

    doc.transcription = text
    doc.save(update_fields=["transcription"])
    return JsonResponse({"ok": True, "text": text})
