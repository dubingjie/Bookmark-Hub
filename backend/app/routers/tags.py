from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Tag, bookmark_tags
from ..schemas import TagCreate, TagWithCount

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.post("", response_model=TagWithCount, status_code=201)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Tag).where(Tag.name == payload.name))
    if existing is not None:
        raise HTTPException(status_code=409, detail="标签名已存在")
    tag = Tag(name=payload.name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagWithCount(id=tag.id, name=tag.name, bookmark_count=0)


@router.get("", response_model=list[TagWithCount])
def list_tags(db: Session = Depends(get_db)):
    # 左连接中间表，统计每个标签关联的书签数量
    stmt = (
        select(Tag, func.count(bookmark_tags.c.bookmark_id).label("bookmark_count"))
        .outerjoin(bookmark_tags, bookmark_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(Tag.id)
    )
    return [
        TagWithCount(id=tag.id, name=tag.name, bookmark_count=count)
        for tag, count in db.execute(stmt).all()
    ]


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    db.delete(tag)  # 中间表关联由外键 CASCADE 清理，书签本身不受影响
    db.commit()
    return Response(status_code=204)
