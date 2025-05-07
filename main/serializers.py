from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *  # Replace with your custom user model


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    avatar = serializers.ImageField(required=False)

    class Meta:
        model = get_user_model()
        fields = ('email', 'password', 'name', 'avatar')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = get_user_model().objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
# accounts/serializers.py


class UserUpdateSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    new_password2 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomUser  # Replace with your custom user model
        fields = ['name', 'avatar', 'old_password',
                  'new_password', 'new_password2']

    def validate(self, data):
        # Password update requested
        if any(field in data for field in ['old_password', 'new_password', 'new_password2']):
            user = self.context['request'].user

            if not data.get('old_password') or not user.check_password(data['old_password']):
                raise serializers.ValidationError(
                    {'old_password': 'Incorrect password.'})
            if data.get('new_password') != data.get('new_password2'):
                raise serializers.ValidationError(
                    {'new_password2': 'Passwords do not match.'})
            if not data.get('new_password'):
                raise serializers.ValidationError(
                    {'new_password': 'New password required.'})

        return data

    def update(self, instance, validated_data):
        # Update basic fields
        instance.name = validated_data.get('name', instance.name)
        if validated_data.get('avatar'):
            instance.avatar = validated_data['avatar']

        # Update password if requested
        if validated_data.get('new_password'):
            instance.set_password(validated_data['new_password'])

        instance.save()
        return instance


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'quantity', 'image', 'created']


class TransactionItemSerializer(serializers.ModelSerializer):
    # include product details
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(
        source='product.image', read_only=True)

    class Meta:
        model = TransactionItem
        fields = [
            'id',
            'product',            # product PK
            'product_name',
            'product_image',
            'quantity',
            'price_at_transaction',
        ]


class TransactionHistorySerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(
        source='transactionitem_set',
        many=True,
        read_only=True
    )
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['id', 'created_at', 'items', 'total_amount']

    def get_total_amount(self, obj):
        return sum([
            item.quantity * float(item.price_at_transaction)
            for item in obj.transactionitem_set.all()
        ])


class TransactionSerializer(serializers.ModelSerializer):
    items = TransactionItemSerializer(source='transactionitem_set', many=True)

    class Meta:
        model = Transaction
        fields = ['id', 'created_at', 'items']
