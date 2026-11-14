from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Note
from app.schemas import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_note(note_id: int, session: Session) -> Note:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заметка не найдена")
    return note


@router.get("", response_model=list[NoteRead])
def list_notes(session: SessionDep) -> list[Note]:
    return list(session.scalars(select(Note).order_by(Note.id.desc())))


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, session: SessionDep) -> Note:
    note = Note(**payload.model_dump())
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, session: SessionDep) -> Note:
    return _get_note(note_id, session)


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(note_id: int, payload: NoteUpdate, session: SessionDep) -> Note:
    note = _get_note(note_id, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    session.commit()
    session.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, session: SessionDep) -> None:
    note = _get_note(note_id, session)
    session.delete(note)
    session.commit()
