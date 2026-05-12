from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, Review as ReviewSchema
from app.db_depends import get_db, get_async_db
from app.auth import get_current_seller



# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", response_model=list[ProductSchema], status_code=200)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    res = await db.scalars(stmt)
    products = res.all()
    return products


@router.post("/", response_model=ProductSchema, status_code=201)
async def create_product(product_create: ProductCreate,
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """
    Создаёт новый товар, привязанный к тек продавцу.
    """
    stmt = select(CategoryModel).where(CategoryModel.id == product_create.category_id,
                                       CategoryModel.is_active == True)
    res = await db.scalars(stmt)
    categoty = res.first()
    if categoty is None:
        raise HTTPException(status_code=400, detail='Category not found or inactive')

    product = ProductModel(**product_create.model_dump(), seller_id=current_user.id)
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return product


@router.get("/category/{category_id}", response_model=list[ProductSchema], status_code=200)
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    stmt_category = select(CategoryModel).where(CategoryModel.id == category_id,
                                                CategoryModel.is_active == True)
    category = ( await db.scalars(stmt_category) ).first()

    if category is None:
        raise HTTPException(status_code=404, detail='Category not found or inactive')

    stmt_products = select(ProductModel).where(ProductModel.category_id == category_id,
                                               ProductModel.is_active == True)
    res = await db.scalars(stmt_products)
    products = res.all()

    return products


@router.get("/{product_id}", response_model=ProductSchema, status_code=200)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    res = await db.scalars(stmt)
    product = res.first()
    if product is None:
        raise HTTPException(status_code=404, detail='Product not found or inactive')

    stmt = select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    res = await db.scalars(stmt)
    if res.first() is None:
        raise HTTPException(status_code=400, detail='Category not found or inactive')

    return product


@router.put("/{product_id}", response_model=ProductSchema, status_code=200)
async def update_product(product_id: int, product_create: ProductCreate,
                         db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """
    Обновляет товар по его ID, если он принадлежит тек продавцу.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    res = await db.scalars(stmt)
    product = res.first()
    if product is None:
        raise HTTPException(status_code=404, detail='Product not found or inactive')

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail='You can only update your own products')

    stmt = select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    res = await db.scalars(stmt)
    category = res.first()
    if category is None:
        raise HTTPException(status_code=400, detail='Category not found or inactive')

    update_data = product_create.model_dump(exclude_unset=True)
    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(**update_data)
    )
    await db.commit()
    await db.refresh(product)

    return product


@router.delete("/{product_id}", response_model=ProductSchema, status_code=200)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db),
                         current_user: UserModel = Depends(get_current_seller)):
    """
    Удаляет товар по его ID, если он принадлежит тек продавцу.
    """
    stmt = select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    res = await db.scalars(stmt)
    product = res.first()
    if product is None:
        raise HTTPException(status_code=404, detail='Product  not found or inactive')

    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail='You can only delete your own products')

    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(is_active=False)
    )
    await db.commit()
    await db.refresh(product)

    return product

@router.get('/{product_id/reviews}', response_model=list[ReviewSchema])
async def get_product_review(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """Получение отзыва о товаре"""
    res = await db.scalars( select(Review).where(Review.product_id == product_id,
                                                  Review.is_active == True) )
    result = res.all()
    if not result:
        raise HTTPException(status_code=404, detail='Not Found')
    return result