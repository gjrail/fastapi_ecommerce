from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.db_depends import get_db, get_async_db
from app.auth import get_current_user


router = APIRouter( prefix='/reviews', tags=['reviews'] )

@router.get('/', response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """ Возвращает список всех отзывов """
    res = await db.scalars( select(ReviewModel).where(ReviewModel.is_active == True) )
    return res.all()


@router.post('/', response_model=ReviewSchema)
async def add_review(review_create: ReviewCreate, db: AsyncSession = Depends(get_async_db),
                        current_user: UserModel = Depends(get_current_user)):
    """Добавление отзыва"""

    if current_user.role != 'buyer':
        HTTPException(status_code=403, detail='User is not buyer')

    res_product = await db.scalars( select(ProductModel).where(ProductModel.id == review_create.product_id,
                                                       ProductModel.is_active == True) )
    product = res_product.first()
    if not product:
        raise HTTPException(status_code=404, detail='Product is not found or inactive')

    if review_create.grade not in range(1,6):
        raise HTTPException(status_code=422, detail='Grade is not in range 1..5')

    #Проверяем, что пользователь уже оценил товар
    res_review = await db.scalars( select(ReviewModel).where(ReviewModel.user_id == current_user.id) )
    exist_review = res_review.first()
    if exist_review:
        raise HTTPException(status_code=409, detail='Review already exists')

    #Создаем обзор, обновляем БД
    review = ReviewModel(**review_create.model_dump(), user_id=current_user.id)
    db.add(review)
    await db.commit()
    await db.refresh(review)

    #Пересчет рейтинга продукта
    res = await db.scalars( select(ReviewModel.grade).where(ReviewModel.product_id == review_create.product_id,
                                                            ReviewModel.is_active == True) )

    data = res.all()
    res_average = round( sum(data) / len(data), 1)

    await db.execute( update(ProductModel).where(ProductModel.id == review_create.product_id)
                      .values(rating=res_average ) )
    await db.commit()
    #await db.refresh()

    return review


@router.delete('/{review_id}')
async def del_review(review_id: int, db: AsyncSession = Depends(get_async_db),
                     current_user: UserModel = Depends(get_current_user)):
    res = await db.scalars( select(ReviewModel).where(ReviewModel.id == review_id ) )
    review = res.first()
    if review is None or review.is_active == False:
        raise HTTPException(status_code=404, detail='Review is not found or inactive')
    if current_user.role != 'admin' and current_user.id != review.user_id:
        raise HTTPException(status_code=403, detail='User is not author or is not admin')

    await db.execute( update(ReviewModel).where(ReviewModel.id == review_id)
                      .values(is_active=False))
    await db.commit()
    await db.refresh(review)

    #После удаления отзыва обновим рейтинг товара
    res = await db.scalars(select(ReviewModel.grade).where(ReviewModel.product_id == review.product_id,
                                                           ReviewModel.is_active == True))
    data = res.all()
    res_average = round(sum(data) / len(data), 1)

    await db.execute(update(ProductModel).where(ProductModel.id == review.product_id)
                     .values(rating=res_average))
    await db.commit()


    return {"message": "Review deleted"}