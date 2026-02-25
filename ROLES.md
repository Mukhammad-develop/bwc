# Brightway Consulting — Admin Role Reference

> **Last updated:** 2026-02-17
> Update this file every time you change role permissions.

---

## Role Hierarchy

```
🛡️ Master Admin  ──► highest privilege
⚡ Admin          ──► full visibility, no team management
👤 Consultant     ──► restricted to assigned users only
```

---

## Roles in Detail

### 🛡️ Master Admin

There are **two types** of master admin accounts:

| Type | How it works |
|------|-------------|
| **Hardcoded (.env)** | Credentials from `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env`. Works even on a blank database. Cannot be deleted via the panel. |
| **Database master** | Created through the Team Management page (or auto-seeded as `bwmaster` on first startup). Can be deleted only by another master admin. |

**What a Master Admin can do:**
- ✅ View **all** users, cases, and chat histories
- ✅ View and download all uploaded files
- ✅ Update case status and payment status
- ✅ View and generate AI reports (daily / weekly / monthly / quarterly)
- ✅ **Create**, **edit display name**, and **delete** any Admin or Consultant account
- ✅ Assign users to Consultants
- ✅ Extract and view AI-generated user profiles
- ✅ Send messages to users directly from the admin panel

---

### ⚡ Admin

A senior staff member who needs full read and operational access but should **not** manage the admin team.

**What an Admin can do:**
- ✅ View **all** users, cases, and chat histories
- ✅ View and download all uploaded files
- ✅ Update case status and payment status
- ✅ View and generate AI reports
- ✅ Extract and view AI-generated user profiles
- ✅ Send messages to users directly from the admin panel
- ❌ Cannot create, edit, or delete any admin/consultant accounts
- ❌ Cannot access the Team Management page

---

### 👤 Consultant

A front-line consultant who works with specific clients.

**What a Consultant can do:**
- ✅ View users **assigned to them** only
- ✅ Read full chat history of assigned users
- ✅ View and download files uploaded by assigned users
- ✅ Send messages to assigned users from the admin panel
- ❌ Cannot see users or cases not assigned to them
- ❌ Cannot access AI Reports
- ❌ Cannot access Team Management
- ❌ Cannot update case or payment statuses

---

## Default Accounts

| Username | Password | Role | Source |
|----------|----------|------|--------|
| `admin` | (from `.env` `ADMIN_PASSWORD`) | Master | `.env` hardcoded |
| `bwmaster` | `Brightway2025!` | Master | Auto-seeded in DB on first startup |

> ⚠️ Change the `bwmaster` password immediately after first login via **My Profile → Change Password**.

---

## Seeded Second Master Admin

On every app startup, the app checks if the `bwmaster` account exists in the database.
If it does not, it creates it automatically with:

- **Username:** `bwmaster` (override via `MASTER2_USERNAME` in `.env`)
- **Password:** `Brightway2025!` (override via `MASTER2_PASSWORD` in `.env`)
- **Display name:** `Brightway Master` (override via `MASTER2_DISPLAY` in `.env`)

This account behaves exactly like any other DB master — it can be renamed, have its password changed through the Profile page, and **can** be deleted by the `.env` master if needed.

---

## Changing Role Permissions

To change what a role can do:

1. Open `web/app.py`
2. The three decorators control route-level access:
   - `@login_required` — any logged-in user
   - `@elevated_required` — Master or Admin
   - `@master_required` — Master only
3. The helper `is_elevated()` returns `True` for Master and Admin.
4. The helper `can_view_user(user_db_id)` returns `True` for Master/Admin unconditionally, and for Consultants only if the user is assigned to them.
5. Update this file after every change.
