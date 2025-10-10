from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("承認ワークフロー - メイン画面（準備中）")

def request_list(request):
    return HttpResponse("申請一覧画面（準備中）")

def pending_list(request):
    return HttpResponse("承認待ち一覧画面（準備中）")