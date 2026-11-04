from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Bookmark
from ..schemas import BookmarkCreate, BookmarkOut, BookmarkUpdate

# Redis 追加
from fastapi.responses import RedirectResponse
from ..redis_client import RANKING_KEY, redis_client


# 查询追加
from sqlalchemy import or_, select
from ..models import Bookmark, Tag


# 文件顶部 import 处追加 Tag
from ..models import Bookmark, Tag

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkOut, status_code=201)
def create_bookmark(payload: BookmarkCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"tags"})
    bookmark = Bookmark(**data)
    bookmark.tags = _resolve_tags(db, payload.tags)
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark

'''
@router.get("", response_model=list[BookmarkOut])
def list_bookmarks(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Bookmark)
        .order_by(Bookmark.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.scalars(stmt).all()
'''

'''
@router.get("", response_model=list[BookmarkOut])
def list_bookmarks(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Bookmark)
        .order_by(Bookmark.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    bookmarks = db.scalars(stmt).all()

    if bookmarks:
        # 用 pipeline 把 N 次 ZSCORE 合并成一次网络往返
        pipe = redis_client.pipeline()
        for b in bookmarks:
            pipe.zscore(RANKING_KEY, str(b.id))
        scores = pipe.execute()
        for b, score in zip(bookmarks, scores):
            b.visits = int(score) if score else 0

    return bookmarks
'''


# 查询更新 2.0
@router.get("", response_model=list[BookmarkOut])
def list_bookmarks(
    keyword: str | None = Query(default=None, max_length=100),
    tag_id: int | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Bookmark)

    # 标签筛选：通过多对多关系 JOIN，只保留绑定了该标签的书签
    if tag_id is not None:
        stmt = stmt.join(Bookmark.tags).where(Tag.id == tag_id)

    # 关键词模糊匹配：标题或备注包含关键词即命中
    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Bookmark.title.like(kw), Bookmark.remark.like(kw)))

    stmt = stmt.order_by(Bookmark.created_at.desc()).offset(offset).limit(limit)
    bookmarks = db.scalars(stmt).all()

    if bookmarks:
        pipe = redis_client.pipeline()
        for b in bookmarks:
            pipe.zscore(RANKING_KEY, str(b.id))
        scores = pipe.execute()
        for b, score in zip(bookmarks, scores):
            b.visits = int(score) if score else 0

    return bookmarks



# Redis 新增路由
@router.get("/top", response_model=list[BookmarkOut])
def top_bookmarks(
    limit: int = Query(default=10, ge=1, le=10),
    db: Session = Depends(get_db),
):
    pairs = redis_client.zrevrange(RANKING_KEY, 0, limit - 1, withscores=True)
    if not pairs:
        return []  # 冷启动：还没有任何访问数据，返回空列表，前端显示占位提示
    ids = [int(member) for member, _ in pairs]
    scores = {int(member): int(score) for member, score in pairs}

    bookmarks = db.scalars(select(Bookmark).where(Bookmark.id.in_(ids))).all()
    by_id = {b.id: b for b in bookmarks}

    result = []
    for bid in ids:                # 按榜单顺序组装，不能直接用数据库返回的顺序
        bookmark = by_id.get(bid)
        if bookmark is None:       # 防御：榜单里的死 ID（书签已删但忘了 ZREM）
            continue
        bookmark.visits = scores[bid]
        result.append(bookmark)
    return result



@router.get("/{bookmark_id}", response_model=BookmarkOut)
def get_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    bookmark = db.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise HTTPException(status_code=404, detail="书签不存在")
    return bookmark


@router.put("/{bookmark_id}", response_model=BookmarkOut)
def update_bookmark(
    bookmark_id: int, payload: BookmarkUpdate, db: Session = Depends(get_db)
):
    bookmark = db.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise HTTPException(status_code=404, detail="书签不存在")
    for field, value in payload.model_dump(exclude_unset=True, exclude={"tags"}).items():
        setattr(bookmark, field, value)
    if payload.tags is not None:  # 传了 tags 才整体替换绑定
        bookmark.tags = _resolve_tags(db, payload.tags)
    db.commit()
    db.refresh(bookmark)
    return bookmark


# @router.delete("/{bookmark_id}", status_code=204)
# def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
#     bookmark = db.get(Bookmark, bookmark_id)
#     if bookmark is None:
#         raise HTTPException(status_code=404, detail="书签不存在")
#     db.delete(bookmark)   # bookmark_tags 关联记录由外键 CASCADE 自动清理
#     db.commit()
#     return Response(status_code=204)


# Redis ：修改
@router.delete("/{bookmark_id}", status_code=204)
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    bookmark = db.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise HTTPException(status_code=404, detail="书签不存在")
    db.delete(bookmark)
    db.commit()                                        # 先提交 MySQL 事务
    redis_client.zrem(RANKING_KEY, str(bookmark_id))   # 再清理 Redis，防止榜单出现死 ID
    return Response(status_code=204)




# 追加一个“按名字获取或创建标签的辅助函数”，并让创建/更新接口处理 tags：
def _resolve_tags(db: Session, names: list[str]) -> list[Tag]:
    """按标签名列表返回 Tag 对象，不存在的名字自动创建"""
    tags = []
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()  # 立即写入以拿到自增 id，但还不提交事务
        tags.append(tag)
    return tags


# Redis 新增
@router.get("/{bookmark_id}/visit")
def visit_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    bookmark = db.get(Bookmark, bookmark_id)
    if bookmark is None:
        raise HTTPException(status_code=404, detail="书签不存在")
    redis_client.zincrby(RANKING_KEY, 1, str(bookmark_id))  # 原子自增
    return RedirectResponse(url=bookmark.url, status_code=302)


