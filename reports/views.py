from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("レポート・出力 - メイン画面（準備中）")

def monthly_pricelist(request):
    return HttpResponse("月次価格表画面（準備中）")

def export_excel(request):
    return HttpResponse("Excel出力画面（準備中）")