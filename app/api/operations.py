from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models import User, UserRole, AccountStatus
from app.models.operations import Meeting, Attendance, Contribution, Payment, PaymentMethod
from app.schemas.operations import MemberUpdate, MeetingCreate, MeetingRead, AttendanceCreate, ContributionCreate, ContributionRead, PaymentCreate, PaymentRead

router = APIRouter(tags=['Members, meetings, contributions and payments'])

def resolve_member(db: Session, identifier: str):
    return db.get(User, identifier) or db.scalar(select(User).where(User.member_id == identifier))
FINANCE_ROLES = (UserRole.ADMIN, UserRole.TREASURER)
MANAGEMENT_ROLES = (UserRole.ADMIN, UserRole.SECRETARY)

@router.get('/members')
def list_members(status_filter: AccountStatus | None = None, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TREASURER, UserRole.SECRETARY))):
    q = select(User).order_by(User.created_at.desc())
    if status_filter: q = q.where(User.status == status_filter)
    return list(db.scalars(q).all())

@router.patch('/members/{member_id}')
def update_member(member_id: str, payload: MemberUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    user = db.get(User, member_id)
    if not user: raise HTTPException(404, 'Member not found')
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(user, key, value)
    db.commit(); db.refresh(user); return user

@router.post('/meetings', response_model=MeetingRead, status_code=201)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*MANAGEMENT_ROLES))):
    item = Meeting(**payload.model_dump(), created_by=actor.id)
    db.add(item); db.commit(); db.refresh(item); return item

@router.get('/meetings', response_model=list[MeetingRead])
def list_meetings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Meeting).order_by(Meeting.starts_at.desc())).all())

@router.post('/meetings/{meeting_id}/attendance', status_code=201)
def mark_attendance(meeting_id: str, payload: AttendanceCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*MANAGEMENT_ROLES))):
    if not db.get(Meeting, meeting_id): raise HTTPException(404, 'Meeting not found')
    member = resolve_member(db, payload.member_id)
    if not member or member.status != AccountStatus.APPROVED: raise HTTPException(404, 'Approved member not found')
    item = Attendance(meeting_id=meeting_id, member_id=member.id, marked_by=actor.id, status=payload.status)
    db.add(item)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, 'Attendance has already been recorded for this member and meeting')
    db.refresh(item); return {'id': item.id, 'meeting_id': item.meeting_id, 'member_id': item.member_id, 'status': item.status, 'marked_at': item.marked_at}

@router.get('/meetings/{meeting_id}/attendance')
def list_attendance(meeting_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.SECRETARY))):
    if not db.get(Meeting, meeting_id): raise HTTPException(404, 'Meeting not found')
    return [{'id': a.id, 'meeting_id': a.meeting_id, 'member_id': a.member_id, 'member_name': name, 'member_code': code, 'status': a.status, 'marked_at': a.marked_at} for a, name, code in db.execute(select(Attendance, User.full_name, User.member_id).join(User, User.id == Attendance.member_id).where(Attendance.meeting_id == meeting_id)).all()]

@router.post('/contributions', response_model=ContributionRead, status_code=201)
def create_contribution(payload: ContributionCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*FINANCE_ROLES))):
    member = resolve_member(db, payload.member_id)
    if not member or member.status != AccountStatus.APPROVED: raise HTTPException(404, 'Approved member not found')
    values = payload.model_dump(); values['member_id'] = member.id
    item = Contribution(**values, created_by=actor.id); db.add(item)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, 'A contribution already exists for this member and period')
    db.refresh(item); return item

@router.get('/contributions')
def list_contributions(member_id: str | None = None, period: str | None = None, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    q = select(Contribution)
    if actor.role == UserRole.MEMBER: member_id = actor.id
    if member_id: q = q.where(Contribution.member_id == member_id)
    if period: q = q.where(Contribution.period == period)
    rows = db.scalars(q.order_by(Contribution.period.desc())).all()
    result = []
    for c in rows:
        paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.contribution_id == c.id)) or Decimal('0')
        result.append({'id': c.id, 'member_id': c.member_id, 'period': c.period, 'amount_due': c.amount_due, 'amount_paid': paid, 'balance': c.amount_due - paid, 'description': c.description})
    return result

@router.post('/payments', response_model=PaymentRead, status_code=201)
def record_payment(payload: PaymentCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles(*FINANCE_ROLES))):
    contribution = db.get(Contribution, payload.contribution_id)
    if not contribution: raise HTTPException(404, 'Contribution not found')
    paid = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.contribution_id == contribution.id)) or Decimal('0')
    if payload.amount > contribution.amount_due - paid: raise HTTPException(400, 'Payment exceeds the outstanding contribution balance')
    payment = Payment(**payload.model_dump(), receipt_number=f'WAL-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}', received_by=actor.id)
    db.add(payment); db.commit(); db.refresh(payment); return payment

@router.get('/payments')
def list_payments(member_id: str | None = None, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    q = select(Payment, Contribution).join(Contribution, Contribution.id == Payment.contribution_id).order_by(Payment.paid_at.desc())
    if actor.role == UserRole.MEMBER: member_id = actor.id
    if member_id: q = q.where(Contribution.member_id == member_id)
    return [{'id': p.id, 'contribution_id': c.id, 'member_id': c.member_id, 'period': c.period, 'amount': p.amount, 'method': p.method.value, 'receipt_number': p.receipt_number, 'paid_at': p.paid_at} for p,c in db.execute(q).all()]

@router.get('/receipts/{receipt_number}.pdf')
def receipt_pdf(receipt_number: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    payment = db.scalar(select(Payment).where(Payment.receipt_number == receipt_number))
    if not payment: raise HTTPException(404, 'Receipt not found')
    contribution = db.get(Contribution, payment.contribution_id)
    if actor.role == UserRole.MEMBER and contribution.member_id != actor.id: raise HTTPException(403, 'You cannot access another member\'s receipt')
    member = db.get(User, contribution.member_id)
    buf = BytesIO(); pdf = canvas.Canvas(buf, pagesize=A4); width, height = A4
    pdf.setTitle(f'WALOMA receipt {receipt_number}')
    pdf.setFont('Helvetica-Bold', 22); pdf.drawString(55, height-65, 'WALOMA')
    pdf.setFont('Helvetica-Bold', 16); pdf.drawString(55, height-105, 'PAYMENT RECEIPT')
    pdf.setFont('Helvetica', 11)
    lines = [('Receipt number', payment.receipt_number), ('Member name', member.full_name), ('Member ID', member.member_id), ('Contribution period', contribution.period), ('Amount received', f'{payment.amount:.2f}'), ('Payment method', payment.method.value.upper()), ('Reference', payment.reference or '—'), ('Payment date (UTC)', payment.paid_at.strftime('%Y-%m-%d %H:%M'))]
    y = height-155
    for label, value in lines:
        pdf.setFont('Helvetica-Bold', 11); pdf.drawString(60, y, label)
        pdf.setFont('Helvetica', 11); pdf.drawString(235, y, str(value)); y -= 30
    pdf.setFont('Helvetica-Oblique', 9); pdf.drawString(60, y-20, 'Thank you. This receipt was generated by the WALOMA Association Management System.')
    pdf.save(); buf.seek(0)
    return StreamingResponse(buf, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{receipt_number}.pdf"'})
