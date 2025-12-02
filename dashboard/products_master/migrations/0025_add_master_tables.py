from django.db import migrations, models
import django.db.models.deletion

def create_master_data(apps, schema_editor):
    """既存データからマスタデータを作成"""
    Product = apps.get_model('products_master', 'Product')
    LivestockType = apps.get_model('products_master', 'LivestockType')
    Category = apps.get_model('products_master', 'Category')
    
    # 既存の畜種データを取得
    livestock_types = set()
    for product in Product.objects.all():
        if product.livestock_type_old:
            livestock_types.add(product.livestock_type_old)
    
    # 既存の分類データを取得
    categories = set()
    for product in Product.objects.all():
        if product.category_old:
            categories.add(product.category_old)
    
    # 畜種マスタを作成
    for i, livestock_type in enumerate(sorted(livestock_types)):
        LivestockType.objects.get_or_create(
            name=livestock_type,
            defaults={'sort_order': i + 1}
        )
    
    # 分類マスタを作成
    for i, category in enumerate(sorted(categories)):
        Category.objects.get_or_create(
            name=category,
            defaults={'sort_order': i + 1}
        )

def migrate_product_data(apps, schema_editor):
    """商品データを新しい外部キー構造に移行"""
    Product = apps.get_model('products_master', 'Product')
    LivestockType = apps.get_model('products_master', 'LivestockType')
    Category = apps.get_model('products_master', 'Category')
    
    for product in Product.objects.all():
        # 畜種の移行
        if product.livestock_type_old:
            try:
                livestock_type = LivestockType.objects.get(name=product.livestock_type_old)
                product.livestock_type_new = livestock_type
            except LivestockType.DoesNotExist:
                pass
        
        # 分類の移行
        if product.category_old:
            try:
                category = Category.objects.get(name=product.category_old)
                product.category_new = category
            except Category.DoesNotExist:
                pass
        
        product.save()

class Migration(migrations.Migration):

    dependencies = [
        ('products_master', '0024_product_sort_num'),
    ]

    operations = [
        # マスタテーブルを作成
        migrations.CreateModel(
            name='LivestockType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='畜種名')),
                ('sort_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'verbose_name': '畜種マスタ',
                'verbose_name_plural': '畜種マスタ',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='分類名')),
                ('sort_order', models.IntegerField(default=0, verbose_name='表示順')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
            ],
            options={
                'verbose_name': '分類マスタ',
                'verbose_name_plural': '分類マスタ',
                'ordering': ['sort_order', 'name'],
            },
        ),
        
        # 既存フィールドをリネーム
        migrations.RenameField(
            model_name='product',
            old_name='livestock_type',
            new_name='livestock_type_old',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='category',
            new_name='category_old',
        ),
        
        # 新しい外部キーフィールドを追加
        migrations.AddField(
            model_name='product',
            name='livestock_type_new',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='products_master.livestocktype', verbose_name='畜種'),
        ),
        migrations.AddField(
            model_name='product',
            name='category_new',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='products_master.category', verbose_name='分類'),
        ),
        
        # マスタデータを作成
        migrations.RunPython(create_master_data),
        
        # 商品データを移行
        migrations.RunPython(migrate_product_data),
        
        # 古いフィールドを削除
        migrations.RemoveField(
            model_name='product',
            name='livestock_type_old',
        ),
        migrations.RemoveField(
            model_name='product',
            name='category_old',
        ),
        
        # 新しいフィールドをリネーム
        migrations.RenameField(
            model_name='product',
            old_name='livestock_type_new',
            new_name='livestock_type',
        ),
        migrations.RenameField(
            model_name='product',
            old_name='category_new',
            new_name='category',
        ),
    ]