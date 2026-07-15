import datetime
from optiply_etl.models import Product, ProductCompositions, Supplier, SupplierProduct, SellOrderWithLines, SellOrder, SellOrderLine, BuyOrder, BuyOrderLine, ReceiptLine, Promotion, PromotionProduct
from optiply_etl.tools import nan_to_none, clean_payload
import pandas as pd
import datetime

def get_product_payload(row):
    # if optiply_id doesn't exist set action="POST"
    action = "POST" if row.get('optiply_id') is None else "PATCH"

    # Conditional logic for unlimitedStock
    if action == "POST" and 'unlimitedStock' not in row:
        unlimited_stock = False
    else:
        unlimited_stock = None if 'unlimitedStock' not in row else bool(row['unlimitedStock'])#bool(row['unlimitedStock']) if 'unlimitedStock' in row else None

    product = {
        "remoteId": row.get('remoteId', None),
        "name": row.get('name', None),
        "skuCode": row.get('skuCode', None),
        "articleCode": row.get('articleCode', None),
        "price": nan_to_none(row.get('price', None)),
        "unlimitedStock": unlimited_stock,#None if 'unlimitedStock' not in row else bool(row['unlimitedStock']),
        "stockLevel": row.get('stockLevel', None),
        "status": row.get('status', None),
        "eanCode": row.get('eanCode', None),
        "assembled": row.get('assembled', None),
        "createdAtRemote": None if pd.isna(row.get('created_at')) else row.get('created_at'),
        "notBeingBought": None if 'notBeingBought' not in row else bool(row['notBeingBought']),
        "minimumStock": row.get('minimumStock', None),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    product = Product(**product)
    product_payload = clean_payload(product.dict())
    return product_payload


def get_product_compositions_payload(row):
    product_compositions = {
        "composedProductId": row.get('composedProductId', None),
        "partProductId": row.get('partProductId', None),
        "partQuantity": row.get('partQuantity', None),
        "remoteId": row.get('remoteId', None),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    product_compositions = ProductCompositions(**product_compositions)
    product_compositions_payload = clean_payload(product_compositions.dict())
    return product_compositions_payload


def get_supplier_payload(row):
    emails = row.get('emails', None)
    if emails is not None:
        # Split the string and strip whitespace to create the list
        emails = [email.strip() for email in emails.split(',')]

    supplier = {
        "name": row.get('name', None),
        "remoteId": row.get('remoteId', None),
        "emails": emails,
        "ignored": row.get('ignored', None),
        "deliveryTime": nan_to_none(row.get('deliveryTime', None)),
        "fixedCosts": nan_to_none(row.get('fixedCosts', None)),
        "userReplenishmentPeriod": nan_to_none(row.get('userReplenishmentPeriod', None)),
        "currency": nan_to_none(row.get('currency', None)),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    supplier = Supplier(**supplier)
    supplier_payload = clean_payload(supplier.dict())
    return supplier_payload


def get_supplier_product_payload(row):
    supplier_product= {
        "name": row.get('name', None),
        "remoteId": row.get('remoteId', None),
        "skuCode": row.get('skuCode', None),
        "articleCode": nan_to_none(row.get('articleCode', None)),
        "status": row.get('status', None),
        "eanCode": row.get('eanCode', None),
        "preferred": row.get('preferred', None),
        "price": nan_to_none(row.get('price', None)),
        "deliveryTime": nan_to_none(row.get('deliveryTime', None)),
        "productId": row.get('productId', None),
        "supplierId": row.get('supplierId', None),
        "lotSize": nan_to_none(row.get('lotSize', None)),
        "minimumPurchaseQuantity": nan_to_none(row.get('minimumPurchaseQuantity', None)),
        "weight": nan_to_none(row.get('weight', None)),
        "volume": nan_to_none(row.get('volume', None)),
        "freeStock": nan_to_none(row.get('freeStock', None)),
        "costPrice": nan_to_none(row.get('costPrice', None)),
        "discountPrice": nan_to_none(row.get('discountPrice', None)),
        "secondaryCurrencyPrice": nan_to_none(row.get('secondPrice', None)),
        "economicOrderQuantity": nan_to_none(row.get('economicOrderQuantity', None)),
        "availabilityDate": nan_to_none(row.get('availabilityDate', None)),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    #validating and cleaning the product payload
    supplier_product = SupplierProduct(**supplier_product)
    supplier_product_payload = clean_payload(supplier_product.dict())
    return supplier_product_payload


def get_sell_order_withlines_payload(row):
    sell_order_withlines = {
        "totalValue": row.get('totalValue', None),
        "remoteId": row.get('remoteId', None),
        "placed": row.get('placed', None),
        "orderLines": row.get('lines', None),
        "completed": nan_to_none(row.get('completed', None)),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    sell_order_withlines = SellOrderWithLines(**sell_order_withlines)
    sell_order_withlines_payload = clean_payload(sell_order_withlines.dict())
    return sell_order_withlines_payload


def get_sell_order_payload(row):
    sell_order = {
        "totalValue": row.get('totalValue', None),
        "remoteId": row.get('remoteId', None),
        "placed": row.get('placed', None),
        "completed": nan_to_none(row.get('completed', None)),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    sell_order = SellOrder(**sell_order)
    sell_order_payload = clean_payload(sell_order.dict())
    return sell_order_payload


def get_sell_order_line_payload(row):
    sell_order_line = {
        "quantity": row.get('quantity', None),
        "sellOrderId":row.get('sellOrderId', None),
        "productId":row.get('productId', None),
        "subtotalValue": row.get('subtotalValue', None),
        "remoteId": row.get('remoteId', None)
    }

    #validating and cleaning the product payload
    sell_order_line = SellOrderLine(**sell_order_line)
    sell_order_line_payload = clean_payload(sell_order_line.dict())
    return sell_order_line_payload


def get_buy_order_payload(row):
    buy_order = {
        "remoteId": row.get('remoteId', None),
        "supplierId": row.get('supplierId', None),
        "placed": row.get('placed', None),
        "totalValue": row.get('totalValue', None),
        "completed": nan_to_none(row.get('completed', None)),
        "expectedDeliveryDate": nan_to_none(row.get('expectedDeliveryDate', None)),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    buy_order = BuyOrder(**buy_order)
    buy_order_payload = clean_payload(buy_order.dict())
    return buy_order_payload


def get_buy_order_line_payload(row):
    buy_order_line = {
        "productId": row.get('productId', None),
        #"productsId": int(float(row['productId'])),
        "quantity": row.get('quantity', None),
        "subtotalValue": row.get('subtotalValue', None),
        "buyOrderId": row.get('buyOrderId', None),
        #"buyOrderId": int(float(row['buyOrderId'])),
        "expectedDeliveryDate": nan_to_none(row.get('expectedDeliveryDate', None)),
        "remoteId": row.get('remoteId', None),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    buy_order_line = BuyOrderLine(**buy_order_line)
    buy_order_line_payload = clean_payload(buy_order_line.dict())
    return buy_order_line_payload


def get_receipt_line_payload(row):
    receipt_line = {
        "occurred": row.get('occurred', None),
        "quantity": row.get('quantity', None),
        "buyOrderLineId":row.get('buyOrderLineId', None),
        "remoteId": row.get('remoteId', None),
        "remoteDataSyncedToDate": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    #validating and cleaning the product payload
    receipt_line = ReceiptLine(**receipt_line)
    receipt_line_payload = clean_payload(receipt_line.dict())
    return receipt_line_payload


def get_promotion_payload(row):
    promotion = {
        "name": row.get('name', None),
        "startDate": row.get('startDate', None),
        "endDate": row.get('endDate', None),
        "upliftType": nan_to_none(row.get('upliftType', None)),
        "upliftIncrease": nan_to_none(row.get('upliftIncrease', None)),
        "enabled": row.get('enabled', None),
        "entireShop": row.get('entireShop', None)
    }

    #validating and cleaning the product payload
    promotion = Promotion(**promotion)
    promotion_payload = clean_payload(promotion.dict())
    return promotion_payload


def get_promotion_product_payload(row):
    promotion_product = {
        "promotionId": row.get('promotionId', None),
        "productId": row.get('productId', None),
        "specificUpliftType": nan_to_none(row.get('specificUpliftType', None)),
        "specificUpliftIncrease": nan_to_none(row.get('specificUpliftIncrease', None))
    }

    #validating and cleaning the product payload
    promotion_product = PromotionProduct(**promotion_product)
    promotion_product_payload = clean_payload(promotion_product.dict())
    return promotion_product_payload


# Dispatch the payload builder according to the entity (moved from the ETL notebook)
def get_payload_function(row, entity):
    if entity == "suppliers":
        return get_supplier_payload(row)
    elif entity == "products":
        return get_product_payload(row)
    elif entity == "productCompositions":
        return get_product_compositions_payload(row)
    elif entity == "supplierProducts":
        return get_supplier_product_payload(row)
    elif entity == "sellOrders":
        return get_sell_order_withlines_payload(row)
    elif entity == "buyOrders":
        return get_buy_order_payload(row)
    elif entity == "buyOrderLines":
        return get_buy_order_line_payload(row)
    elif entity == "receiptLines":
        return get_receipt_line_payload(row)
    else:
        raise ValueError("Invalid entity type")
