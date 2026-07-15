from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Product(BaseModel):
    name: str
    unlimitedStock: Optional[bool]
    stockLevel: int
    skuCode: Optional[str]
    eanCode: Optional[str]
    articleCode: Optional[str]
    price: Optional[float] # Round to 2 decimal places
    remoteId: Optional[str]
    remoteDataSyncedToDate: Optional[datetime]
    status: Optional[str] # enabled or disabled
    assembled: Optional[bool]
    createdAtRemote: Optional[datetime]
    notBeingBought: Optional[bool]
    minimumStock: Optional[int]

class ProductCompositions(BaseModel):
    composedProductId: str
    partProductId: str
    partQuantity: int
    remoteId: Optional[str]
    batchQuantity: Optional[int]
    remoteDataSyncedToDate: datetime

class Supplier(BaseModel):
    name: str
    remoteId: str
    emails: Optional[List[str]]
    ignored: Optional[bool]
    deliveryTime: Optional[int]
    fixedCosts: Optional[float] # Round to 2 decimal places
    remoteDataSyncedToDate: datetime
    userReplenishmentPeriod: Optional[int]
    currency: Optional[str]

class SupplierProduct(BaseModel):
    name: str
    remoteId: str
    price: Optional[float] # Round to 2 decimal places
    skuCode: Optional[str]
    articleCode: Optional[str]
    status: Optional[str] # enabled or disabled
    eanCode: Optional[str]
    lotSize: Optional[int]
    minimumPurchaseQuantity: Optional[int]
    deliveryTime: Optional[int]
    productId: str
    supplierId: str
    remoteDataSyncedToDate: Optional[datetime]
    preferred: Optional[bool]
    weight: Optional[float] # in grams. Round to 2 decimal places
    volume: Optional[float] # in cubic centimeters. Round to 2 decimal places
    freeStock: Optional[int]
    costPrice: Optional[float]
    discountPrice: Optional[float]
    economicOrderQuantity: Optional[int]
    secondaryCurrencyPrice: Optional[float]
    availabilityDate: Optional[datetime]

class SellOrderWithLines(BaseModel):
    totalValue: float # Round to 2 decimal places
    remoteId: Optional[str]
    placed: datetime
    orderLines: list
    completed: Optional[datetime]
    remoteDataSyncedToDate: Optional[datetime]

class SellOrder(BaseModel):
    totalValue: float # Round to 2 decimal places
    remoteId: Optional[str]
    placed: datetime
    completed: Optional[datetime]
    remoteDataSyncedToDate: Optional[datetime]

class SellOrderLine(BaseModel):
    quantity: int
    subtotalValue: float # Round to 2 decimal places
    productId: str
    remoteId: Optional[str]

class BuyOrder(BaseModel):
    remoteId: str
    supplierId: str
    placed: datetime
    totalValue: float # Round to 2 decimal places
    remoteDataSyncedToDate: Optional[datetime]
    completed: Optional[datetime]
    expectedDeliveryDate: Optional[datetime]

class BuyOrderLine(BaseModel):
    quantity: int
    subtotalValue: float # Round to 2 decimal places
    buyOrderId: int
    productId: int
    remoteId: Optional[str]
    remoteDataSyncedToDate: Optional[datetime]
    expectedDeliveryDate: Optional[datetime]

class ReceiptLine(BaseModel):
    occurred: datetime
    quantity: int
    buyOrderLineId: str
    remoteId: Optional[str]
    remoteDataSyncedToDate: Optional[datetime]

class Promotion(BaseModel):
    name: str
    startDate: datetime
    endDate: datetime
    upliftType: Optional[str]
    upliftIncrease: Optional[int]
    enabled: Optional[bool]
    entireShop: Optional[bool]

class PromotionProduct(BaseModel):
    promotionId: str
    productId: str
    specificUpliftType: Optional[str]
    specificUpliftIncrease: Optional[int]