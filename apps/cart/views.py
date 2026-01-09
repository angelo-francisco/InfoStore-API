import random
import string

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer
from apps.products.models import Product


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def handle_cart(request):
    """
    Endpoint unify for create and get cart.
    - POST: Create a cart (anonymos or user).
    - GET: Get cart (anonymos with ?code= or auth user).
    """
    if request.method == "POST":
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
            if created:
                cart.cart_code = "".join(
                    random.choices(string.ascii_letters + string.digits, k=11)
                )
                cart.save()
        else:
            cart_code = "".join(
                random.choices(string.ascii_letters + string.digits, k=11)
            )
            cart = Cart.objects.create(cart_code=cart_code)

        serializer = CartSerializer(cart)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    elif request.method == "GET":
        cart_code = request.query_params.get("code")

        if cart_code:
            try:
                cart = Cart.objects.get(cart_code=cart_code)
                serializer = CartSerializer(cart)
                return Response(serializer.data)
            except Cart.DoesNotExist:
                return Response({"cartitems": [], "cart_code": cart_code})

        elif request.user.is_authenticated:
            try:
                cart = Cart.objects.filter(user=request.user).first()
                if not cart:
                    cart = Cart.objects.create(user=request.user)
        
                    cart.cart_code = "".join(
                        random.choices(string.ascii_letters + string.digits, k=11)
                    )
                    cart.save()
                serializer = CartSerializer(cart)
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "error": "É necessário estar autenticado ou fornecer um código de carrinho."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def add_to_cart(request):
    cart_code = request.data.get("cart_code")
    product_id = request.data.get("product_id")
    quantity = request.data.get("quantity", 1)

    try:
        # Buscar ou criar o carrinho
        cart = Cart.objects.get(cart_code=cart_code)
        product = Product.objects.get(id=product_id)

        # Buscar ou criar o item do carrinho
        cartitem, created = CartItem.objects.get_or_create(
            product=product, cart=cart, defaults={"quantity": 0}
        )

        if created:
            cartitem.quantity = quantity
        else:
            cartitem.quantity += quantity

        cartitem.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Cart.DoesNotExist:
        return Response(
            {"error": "Carrinho não encontrado."}, status=status.HTTP_404_NOT_FOUND
        )
    except Product.DoesNotExist:
        return Response(
            {"error": "Produto não encontrado."}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_cartitem_quantity(request):
    cartitem_id = request.data.get("item_id")
    quantity = request.data.get("quantity")

    try:
        quantity = int(quantity)
        if quantity <= 0:
            return Response(
                {"error": "A quantidade deve ser maior que zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cartitem = CartItem.objects.get(id=cartitem_id)

        if cartitem.cart.user and cartitem.cart.user != request.user:
            return Response(
                {"error": "Você não tem permissão para modificar este item."},
                status=status.HTTP_403_FORBIDDEN,
            )

        cartitem.quantity = quantity
        cartitem.save()

        serializer = CartItemSerializer(cartitem)
        return Response(
            {
                "data": serializer.data,
                "message": "Item do carrinho atualizado com sucesso!",
            }
        )
    except CartItem.DoesNotExist:
        return Response(
            {"error": "Item do carrinho não encontrado."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError:
        return Response(
            {"error": "Quantidade inválida."}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_cartitem(request, pk):
    try:
        cartitem = CartItem.objects.get(id=pk)

        if cartitem.cart.user and cartitem.cart.user != request.user:
            return Response(
                {"error": "Você não tem permissão para excluir este item"},
                status=status.HTTP_403_FORBIDDEN,
            )

        cartitem.delete()
        return Response(
            {"message": "Item do carrinho excluído com sucesso"},
            status=status.HTTP_204_NO_CONTENT,
        )
    except CartItem.DoesNotExist:
        return Response(
            {"error": "Item do carrinho não encontrado"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merge_carts(request):
    try:
        user_cart, created = Cart.objects.get_or_create(user=request.user)
        if created:
            user_cart.cart_code = "".join(
                random.choices(string.ascii_letters + string.digits, k=11)
            )
            user_cart.save()

        # Get the temporary cart (if exist)
        temp_cart_code = request.data.get("temp_cart_code")
        if temp_cart_code:
            try:
                temp_cart = Cart.objects.get(cart_code=temp_cart_code)
                # Move items from temporary cart to user cart
                for item in temp_cart.cartitems.all():
                    CartItem.objects.update_or_create(
                        cart=user_cart,
                        product=item.product,
                        defaults={"quantity": item.quantity},
                    )
                temp_cart.delete()
            except Cart.DoesNotExist:
                pass

        serializer = CartSerializer(user_cart)
        return Response(serializer.data)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
