from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _normalize_url(v: str) -> str:
    v = v.strip()
    if not v.startswith(("http://", "https://")):
        v = "https://" + v
    return v


class BookmarkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=1024)
    remark: str | None = None
    tags: list[str] = []          # 新增：标签名列表，新标签自动创建
    # ...原有的两个 validator 保持不变

    @field_validator("title", "remark", mode="before")
    @classmethod
    def strip_text(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, v):
        return _normalize_url(v) if isinstance(v, str) else v


class BookmarkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=1024)
    remark: str | None = None
    tags: list[str] | None = None  # 新增：传了则整体替换标签绑定；不传则不动
    # ...原有的两个 validator 保持不变

    @field_validator("title", "remark", mode="before")
    @classmethod
    def strip_text(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, v):
        return _normalize_url(v) if isinstance(v, str) else v


class TagOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class BookmarkOut(BaseModel):
    id: int
    title: str
    url: str
    remark: str | None
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []
    visits: int = 0        # 新增：实时访问次数，接口返回前从 Redis 注入

    model_config = {"from_attributes": True}


# ===== 追加到 schemas.py 末尾 =====

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v):
        return v.strip() if isinstance(v, str) else v


class TagWithCount(BaseModel):
    id: int
    name: str
    bookmark_count: int

    model_config = {"from_attributes": True}
