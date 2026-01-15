# Generated manually for memo field addition

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products_master', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricehistory',
            name='memo',
            field=models.TextField(blank=True, help_text='作業者と申請者間のコミュニケーション用', null=True, verbose_name='メモ'),
        ),
        migrations.AddField(
            model_name='pricehistoryapproval',
            name='memo',
            field=models.TextField(blank=True, help_text='作業者と申請者間のコミュニケーション用', null=True, verbose_name='メモ'),
        ),
    ]