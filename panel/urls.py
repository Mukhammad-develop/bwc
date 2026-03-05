from django.urls import path
from panel.views import auth, dashboard, cases, users, files, reports, admins, notifications, import_chat, services_admin

app_name = "panel"

urlpatterns = [
    # Auth
    path("",                    auth.login_view,   name="login"),
    path("admin/login",         auth.login_view,   name="login"),
    path("admin/logout",        auth.logout_view,  name="logout"),
    path("admin/profile",       auth.profile_view, name="profile"),

    # Dashboard
    path("admin",               dashboard.dashboard, name="dashboard"),
    path("admin/",              dashboard.dashboard),

    # Cases
    path("admin/cases",                         cases.cases_list,     name="cases"),
    path("admin/cases/<int:case_id>",           cases.case_detail,    name="case_detail"),
    path("admin/cases/<int:case_id>/update",    cases.case_update,    name="case_update"),
    path("admin/cases/<int:case_id>/progress",  cases.case_progress,  name="case_progress"),

    # Users
    path("admin/users",                                  users.users_list,    name="users"),
    path("admin/users/<int:user_db_id>",                 users.user_profile,  name="user_profile"),
    path("admin/users/<int:user_db_id>/send",            users.send_message,  name="send_message"),
    path("admin/users/<int:user_db_id>/poll",            users.poll_messages, name="poll_messages"),
    path("admin/users/<int:user_db_id>/extract-profile", users.extract_profile, name="extract_profile"),
    path("admin/users/<int:user_db_id>/assign",          users.assign_user,   name="assign_user"),
    # Notes
    path("admin/users/<int:user_db_id>/notes/add",                  users.note_add,    name="note_add"),
    path("admin/users/<int:user_db_id>/notes/<int:note_id>/edit",   users.note_edit,   name="note_edit"),
    path("admin/users/<int:user_db_id>/notes/<int:note_id>/delete", users.note_delete, name="note_delete"),

    # Files
    path("admin/files/local/<path:filename>",            files.local_file,          name="local_file"),
    path("admin/files/view/<path:file_id>",              files.file_view,           name="file_view"),
    path("admin/files/download/<path:file_id>",          files.file_download,       name="file_download"),
    path("admin/documents/<int:doc_id>/transcribe",      files.transcribe_document, name="transcribe_document"),

    # Reports
    path("admin/reports",                          reports.reports_list,    name="reports"),
    path("admin/reports/generate/<str:report_type>", reports.generate_report, name="generate_report"),
    path("admin/reports/<int:report_id>",          reports.report_detail,   name="report_detail"),

    # Admin management
    path("admin/admins",                     admins.admins_list, name="admins"),
    path("admin/admins/add",                 admins.add_admin,   name="add_admin"),
    path("admin/admins/<int:admin_id>/delete", admins.delete_admin, name="delete_admin"),

    # Notifications
    path("admin/notifications",                          notifications.notifications_list,    name="notifications"),
    path("admin/notifications/<int:notif_id>/read",      notifications.notif_read,            name="notif_read"),
    path("admin/notifications/read-all",                 notifications.notif_read_all,        name="notif_read_all"),
    path("admin/notifications/preview",                  notifications.notif_preview,         name="notif_preview"),
    path("admin/notifications/mark-preview-read",        notifications.notif_mark_preview_read, name="notif_mark_preview_read"),

    # Import chat
    path("admin/import-chat",                  import_chat.import_chat,   name="import_chat"),
    path("admin/import-chat/<int:req_id>/status", import_chat.import_status, name="import_status"),

    # Services management
    path("admin/services",                          services_admin.services_list,  name="services_list"),
    path("admin/services/add",                      services_admin.service_add,    name="service_add"),
    path("admin/services/<slug:slug>/edit",          services_admin.service_edit,   name="service_edit"),
    path("admin/services/<slug:slug>/delete",        services_admin.service_delete, name="service_delete"),
    path("admin/services/<slug:slug>/toggle",        services_admin.service_toggle, name="service_toggle"),
]
