from typing import Any, Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get(self, id: Any) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def get_by(self, **filters) -> ModelType | None:
        result = await self.session.execute(select(self.model).filter_by(**filters))
        return result.scalar_one_or_none()

    async def list(self, **filters) -> list[ModelType]:
        result = await self.session.execute(select(self.model).filter_by(**filters).order_by(self.model.id))
        return list(result.scalars().all())

    async def update(self, id: Any, **values) -> ModelType | None:
        instance = await self.get(id)
        if instance is None:
            return None
        for key, value in values.items():
            setattr(instance, key, value)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: Any) -> bool:
        instance = await self.get(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.commit()
        return True
