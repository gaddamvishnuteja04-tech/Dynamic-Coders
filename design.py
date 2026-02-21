"""
app/api/design.py
=================
Design Generation API – image upload, AI analysis, project management.

Routes:
  POST /api/design/generate          – Upload image + run AI design analysis
  GET  /api/design/projects          – List user's design projects
  GET  /api/design/projects/<id>     – Get single project with full AI result
  DELETE /api/design/projects/<id>   – Delete a project
  POST /api/design/projects/<id>/rate – Submit a star rating + feedback
"""

import os

from flask import Blueprint, request, current_app, send_from_directory
from flask_login import current_user

from app import db, limiter
from app.models.design import DesignProject
from app.utils.security import (
    api_success, api_error, login_required_api,
    ai_quota_required, validate_image_file,
    generate_secure_filename, sanitise_text, paginate_query,
)

design_bp = Blueprint("design", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# GENERATE DESIGN  (core endpoint)
# ─────────────────────────────────────────────────────────────────────────────
@design_bp.post("/generate")
@login_required_api
@ai_quota_required
@limiter.limit("30 per hour")
def generate_design():
    """
    Accept a room image, run AI design analysis, and return structured JSON.

    Form fields (multipart/form-data):
        image       (file, required)  – room photo
        style       (str, optional)   – design style, default 'Modern'
        room_type   (str, optional)   – e.g. 'Living Room', 'Bedroom'
        room_length (float, optional) – room length in feet
        room_width  (float, optional) – room width in feet
        title       (str, optional)   – project name

    Response JSON:
        {
          "project_id": 42,
          "status": "completed",
          "ai_result": {
            "furniture":     [...],
            "color_scheme":  [...],
            "placement":     {...},
            "design_tips":   [...],
            "estimated_budget_inr": {...}
          }
        }
    """
    # ── 1. Validate file presence ─────────────────────────────────────────────
    if "image" not in request.files:
        return api_error("No image file provided. Include 'image' in form-data.", 400)

    file = request.files["image"]
    is_valid, validation_err = validate_image_file(file)
    if not is_valid:
        return api_error(validation_err, 400)

    # ── 2. Extract and sanitise form parameters ───────────────────────────────
    style       = sanitise_text(request.form.get("style",       "Modern"),   100)
    room_type   = sanitise_text(request.form.get("room_type",   "Living Room"), 80)
    title       = sanitise_text(request.form.get("title",       ""),         200)

    room_length = room_width = None
    try:
        if request.form.get("room_length"):
            room_length = float(request.form["room_length"])
        if request.form.get("room_width"):
            room_width  = float(request.form["room_width"])
    except (ValueError, TypeError):
        return api_error("room_length and room_width must be numeric values.", 400)

    # ── 3. Save uploaded file ─────────────────────────────────────────────────
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = generate_secure_filename(file.filename, user_id=current_user.id)
    image_path = os.path.join(upload_dir, safe_name)

    try:
        file.save(image_path)
        current_app.logger.info(
            "Image saved: user=%d file=%s size=%d bytes",
            current_user.id, safe_name, os.path.getsize(image_path)
        )
    except Exception as e:
        current_app.logger.error("File save error: %s", e)
        return api_error("Failed to save uploaded file.", 500)

    # ── 4. Create project record (status=processing) ──────────────────────────
    project = DesignProject(
        user_id        = current_user.id,
        title          = title or f"{style} – {room_type}",
        image_path     = image_path,
        image_filename = safe_name,
        style          = style,
        room_type      = room_type,
        room_length    = room_length,
        room_width     = room_width,
        status         = "processing",
    )

    try:
        db.session.add(project)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Project DB insert error: %s", e)
        return api_error("Failed to create design project.", 500)

    # ── 5. Run AI analysis ─────────────────────────────────────────────────────
    try:
        from ai_engine import generate_design as ai_generate

        dimensions = {
            "length": room_length,
            "width":  room_width,
        } if (room_length and room_width) else None

        result = ai_generate(
            image_path = image_path,
            style      = style,
            room_type  = room_type,
            dimensions = dimensions,
        )

        confidence = result.get("project_meta", {}).get("confidence", 0.0)
        project.mark_completed(result, confidence)
        current_user.consume_ai_quota()
        db.session.commit()

        current_app.logger.info(
            "AI design complete: project_id=%d style=%s confidence=%.3f",
            project.id, style, confidence
        )

    except Exception as e:
        project.mark_failed(str(e))
        db.session.commit()
        current_app.logger.error("AI generation error: project_id=%d – %s", project.id, e, exc_info=True)
        return api_error(
            "AI analysis failed. Your image has been saved and will be retried.",
            500,
            project_id=project.id,
        )

    # ── 6. Build and return structured response ───────────────────────────────
    ai_result = project.ai_result or {}
    return api_success(
        data={
            "project_id":   project.id,
            "title":        project.title,
            "status":       project.status,
            "style":        project.style,
            "room_type":    project.room_type,
            "ai_confidence": project.ai_confidence,
            "image_url":    f"/api/design/images/{safe_name}",
            "ai_result": {
                "furniture":              ai_result.get("furniture", []),
                "color_scheme":          ai_result.get("color_scheme", []),
                "placement":             ai_result.get("placement", {}),
                "design_tips":           ai_result.get("design_tips", []),
                "estimated_budget_inr":  ai_result.get("estimated_budget_inr", {}),
                "project_meta":          ai_result.get("project_meta", {}),
            },
            "quota_remaining": max(
                0,
                current_user.ai_analyses_limit - current_user.ai_analyses_used
            ),
        },
        message="Design analysis complete!",
        status_code=201,
    )


# ─────────────────────────────────────────────────────────────────────────────
# LIST PROJECTS
# ─────────────────────────────────────────────────────────────────────────────
@design_bp.get("/projects")
@login_required_api
def list_projects():
    """
    Return paginated list of the authenticated user's design projects.

    Query params:
        page     (int, default 1)
        per_page (int, default 20, max 100)
        status   (str, optional) filter by status
    """
    page     = max(1, request.args.get("page",     1,  type=int))
    per_page = max(1, request.args.get("per_page", 20, type=int))
    status   = request.args.get("status")

    query = DesignProject.query.filter_by(user_id=current_user.id).order_by(
        DesignProject.created_at.desc()
    )
    if status:
        query = query.filter_by(status=status)

    paged = paginate_query(query, page=page, per_page=per_page)
    return api_success(data=paged)


# ─────────────────────────────────────────────────────────────────────────────
# GET SINGLE PROJECT
# ─────────────────────────────────────────────────────────────────────────────
@design_bp.get("/projects/<int:project_id>")
@login_required_api
def get_project(project_id: int):
    """Return full details of a single design project (including AI result)."""
    project = DesignProject.query.filter_by(
        id=project_id, user_id=current_user.id
    ).first_or_404()

    return api_success(data=project.to_dict(include_result=True))


# ─────────────────────────────────────────────────────────────────────────────
# DELETE PROJECT
# ─────────────────────────────────────────────────────────────────────────────
@design_bp.delete("/projects/<int:project_id>")
@login_required_api
def delete_project(project_id: int):
    """Delete a design project and its associated image file."""
    project = DesignProject.query.filter_by(
        id=project_id, user_id=current_user.id
    ).first_or_404()

    # Remove image file from disk
    if project.image_path and os.path.isfile(project.image_path):
        try:
            os.remove(project.image_path)
        except OSError as e:
            current_app.logger.warning("Could not delete image file: %s", e)

    try:
        db.session.delete(project)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error("Could not delete project.", 500)

    return api_success(message=f"Project #{project_id} deleted.")


# ─────────────────────────────────────────────────────────────────────────────
# RATE / FEEDBACK
# ─────────────────────────────────────────────────────────────────────────────
@design_bp.post("/projects/<int:project_id>/rate")
@login_required_api
def rate_project(project_id: int):
    """
    Submit a rating and optional feedback for a completed project.

    Body (JSON):
        rating   (int, 1-5, required)
        feedback (str, optional, max 500 chars)
    """
    project = DesignProject.query.filter_by(
        id=project_id, user_id=current_user.id
    ).first_or_404()

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")

    if not isinstance(rating, int) or rating not in range(1, 6):
        return api_error("Rating must be an integer between 1 and 5.", 400)

    project.user_rating   = rating
    project.user_feedback = sanitise_text(data.get("feedback", ""), 500)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return api_error("Failed to save rating.", 500)

    return api_success(message="Thank you for your feedback!", data={"rating": rating})


# ─────────────────────────────────────────────────────────────────────────────
# SERVE UPLOADED IMAGES
# ─────────────────────────────────────────────────────────────────────────────
@design_bp.get("/images/<path:filename>")
@login_required_api
def serve_image(filename: str):
    """Serve an uploaded room image (only to its owner)."""
    # Verify ownership
    project = DesignProject.query.filter_by(
        image_filename=filename, user_id=current_user.id
    ).first()
    if not project:
        return api_error("Image not found.", 404)

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(upload_dir, filename)
