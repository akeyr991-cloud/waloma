import csv, json
from io import StringIO, BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import User, UserRole, Notification, AuditLog, SyncOperation, Contribution, Payment, Meeting, Attendance

router = APIRouter(tags=['Notifications, reports, synchronization and audit'])
MANAGERS = (UserRole.ADMIN, UserRole.SECRETARY)

class AnnouncementIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=2, max_length=5000)
    scheduled_at: datetime | None = None

class SyncIn(BaseModel):
    client_operation_id: str = Field(min_length=8, max_length=80)
    operation_type: str = Field(min_length=2, max_length=80)
    payload: dict

@router.post('/announcements', status_code=201)
def publish_announcement(body: AnnouncementIn, db: Session = Depends(get_db), actor: User = Depends(require_roles(*MANAGERS))):
    now = datetime.now(timezone.utc)
    users = db.scalars(select(User).where(User.is_active.is_(True), User.status == 'approved')).all()
    published = body.scheduled_at is None or body.scheduled_at <= now
    for user in users:
        db.add(Notification(user_id=user.id, title=body.title, message=body.message, scheduled_at=body.scheduled_at, published_at=now if published else None))
    db.add(AuditLog(actor_id=actor.id, action='announcement.created', entity_type='announcement', details=json.dumps({'title': body.title, 'recipients': len(users)})))
    db.commit()
    return {'title': body.title, 'recipients': len(users), 'scheduled': not published, 'scheduled_at': body.scheduled_at}

@router.get('/notifications')
def my_notifications(unread_only: bool = False, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    q = select(Notification).where(Notification.user_id == actor.id, Notification.published_at.is_not(None))
    if unread_only: q = q.where(Notification.is_read.is_(False))
    return list(db.scalars(q.order_by(Notification.created_at.desc()).limit(100)).all())

@router.patch('/notifications/{notification_id}/read')
def mark_notification_read(notification_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == actor.id))
    if not item: raise HTTPException(404, 'Notification not found')
    item.is_read = True; db.commit(); return {'status': 'read'}

@router.get('/reports/summary')
def report_summary(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TREASURER))):
    due = db.scalar(select(func.coalesce(func.sum(Contribution.amount_due), 0))) or 0
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))) or 0
    return {'contributions_due': float(due), 'payments_received': float(paid), 'outstanding_balance': float(due-paid), 'members': db.scalar(select(func.count()).select_from(User)) or 0, 'meetings': db.scalar(select(func.count()).select_from(Meeting)) or 0}

@router.get('/reports/payments.csv')
def export_payments_csv(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TREASURER))):
    rows = db.execute(select(Payment, Contribution, User).join(Contribution, Payment.contribution_id == Contribution.id).join(User, Contribution.member_id == User.id).order_by(Payment.paid_at.desc())).all()
    output = StringIO(); writer = csv.writer(output)
    writer.writerow(['Receipt Number','Member ID','Member Name','Period','Amount','Method','Paid At UTC'])
    for payment, contribution, member in rows:
        writer.writerow([payment.receipt_number, member.member_id, member.full_name, contribution.period, str(payment.amount), payment.method.value, payment.paid_at.isoformat()])
    return StreamingResponse(iter([output.getvalue()]), media_type='text/csv', headers={'Content-Disposition':'attachment; filename="waloma-payments.csv"'})

@router.post('/sync/operations', status_code=202)
def queue_offline_operation(body: SyncIn, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    existing = db.scalar(select(SyncOperation).where(SyncOperation.user_id == actor.id, SyncOperation.client_operation_id == body.client_operation_id))
    if existing: return {'id': existing.id, 'status': existing.status, 'duplicate': True}
    item = SyncOperation(user_id=actor.id, client_operation_id=body.client_operation_id, operation_type=body.operation_type, payload_json=json.dumps(body.payload))
    db.add(item); db.add(AuditLog(actor_id=actor.id, action='offline.operation.received', entity_type='sync_operation', details=body.client_operation_id)); db.commit(); db.refresh(item)
    return {'id': item.id, 'status': item.status, 'duplicate': False, 'message': 'Operation queued for administrator review; no financial transaction was applied automatically.'}

@router.get('/sync/operations')
def list_sync_operations(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    q = select(SyncOperation)
    if actor.role == UserRole.MEMBER: q = q.where(SyncOperation.user_id == actor.id)
    return list(db.scalars(q.order_by(SyncOperation.created_at.desc()).limit(200)).all())

@router.get('/audit-logs')
def audit_logs(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)).all())

@router.post('/announcements/publish-due')
def publish_due_announcements(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    now = datetime.now(timezone.utc)
    due = db.scalars(select(Notification).where(Notification.published_at.is_(None), Notification.scheduled_at <= now)).all()
    for item in due: item.published_at = now
    db.commit()
    return {'published_notifications': len(due)}


@router.get('/reports/payments.xlsx')
def export_payments_excel(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TREASURER))):
    rows = db.execute(select(Payment, Contribution, User).join(Contribution, Payment.contribution_id == Contribution.id).join(User, Contribution.member_id == User.id).order_by(Payment.paid_at.desc())).all()
    book = Workbook(); sheet = book.active; sheet.title = 'Payments'
    sheet.append(['Receipt Number','Member ID','Member Name','Period','Amount','Method','Paid At UTC'])
    for payment, contribution, member in rows:
        sheet.append([payment.receipt_number, member.member_id, member.full_name, contribution.period, float(payment.amount), payment.method.value, payment.paid_at.isoformat()])
    sheet.freeze_panes = 'A2'; sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        letter = column[0].column_letter; sheet.column_dimensions[letter].width = min(32, max(14, max(len(str(cell.value or '')) for cell in column)+2))
    buf=BytesIO(); book.save(buf); buf.seek(0)
    return StreamingResponse(buf, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename="waloma-payments.xlsx"'})

@router.get('/reports/summary.pdf')
def export_summary_pdf(db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TREASURER))):
    due=float(db.scalar(select(func.coalesce(func.sum(Contribution.amount_due),0))) or 0); paid=float(db.scalar(select(func.coalesce(func.sum(Payment.amount),0))) or 0)
    members=db.scalar(select(func.count()).select_from(User)) or 0; meetings=db.scalar(select(func.count()).select_from(Meeting)) or 0
    buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4); _,height=A4
    pdf.setTitle('WALOMA Summary Report'); pdf.setFont('Helvetica-Bold',22); pdf.drawString(55,height-65,'WALOMA')
    pdf.setFont('Helvetica-Bold',16); pdf.drawString(55,height-105,'ASSOCIATION SUMMARY REPORT')
    pdf.setFont('Helvetica',12); y=height-155
    for label,value in [('Contributions due',f'{due:.2f}'),('Payments received',f'{paid:.2f}'),('Outstanding balance',f'{due-paid:.2f}'),('Members',str(members)),('Meetings',str(meetings)),('Generated (UTC)',datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))]:
        pdf.drawString(60,y,f'{label}: {value}'); y-=28
    pdf.save(); buf.seek(0)
    return StreamingResponse(buf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="waloma-summary.pdf"'})
