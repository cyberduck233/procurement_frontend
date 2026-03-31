from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import json
from .models import ReportPage, HistoricalProject, OngoingProject


def ai_analysis(request):
    """AI 一键分析中间页面"""
    keyword = request.GET.get('search', '').strip()
    if not keyword:
        return render(request, 'reports/ai_analysis.html', {'keyword': '未指定关键词'})
    return render(request, 'reports/ai_analysis.html', {'keyword': keyword})

@csrf_exempt
@require_POST
def update_report_content(request, report_id):
    try:
        data = json.loads(request.body)
        field = data.get('field')
        content = data.get('content')

        allowed_fields = ['market_supply_analysis', 'market_trend_analysis', 'ai_summary_analysis']
        if field not in allowed_fields:
            return JsonResponse({'success': False, 'error': 'Invalid field'}, status=400)

        report = ReportPage.objects.get(id=report_id)
        setattr(report, field, content)
        report.save_revision().publish()
        
        return JsonResponse({'success': True, 'message': 'Saved successfully'})
        
    except ReportPage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def filter_historical_projects(request, report_id):
    report = get_object_or_404(ReportPage, id=report_id)
    projects = HistoricalProject.objects.filter(page=report)

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        projects = projects.filter(
            Q(project_name__icontains=q) |
            Q(procurement_unit__icontains=q) |
            Q(supplier_name__icontains=q)
        )

    # 2. Time Filter
    time_filter = request.GET.get('time', 'all')
    now = timezone.now().date()
    if time_filter == '1m':
        start_date = now - timedelta(days=30)
        projects = projects.filter(procurement_time__gte=start_date)
    elif time_filter == '3m':
        start_date = now - timedelta(days=90)
        projects = projects.filter(procurement_time__gte=start_date)
    elif time_filter == '6m':
        start_date = now - timedelta(days=180)
        projects = projects.filter(procurement_time__gte=start_date)
    elif time_filter == '1y':
        start_date = now - timedelta(days=365)
        projects = projects.filter(procurement_time__gte=start_date)
    elif time_filter == '3y':
        start_date = now - timedelta(days=365*3)
        projects = projects.filter(procurement_time__gte=start_date)

    # 3. Amount Filter (Transaction Amount)
    amount_filter = request.GET.get('amount', 'all')
    if amount_filter == '0-10':
        projects = projects.filter(transaction_amount__lt=10)
    elif amount_filter == '10-50':
        projects = projects.filter(transaction_amount__gte=10, transaction_amount__lt=50)
    elif amount_filter == '50-100':
        projects = projects.filter(transaction_amount__gte=50, transaction_amount__lt=100)
    elif amount_filter == '100-500':
        projects = projects.filter(transaction_amount__gte=100, transaction_amount__lt=500)
    elif amount_filter == '500-1000':
        projects = projects.filter(transaction_amount__gte=500, transaction_amount__lt=1000)
    elif amount_filter == '1000-5000':
        projects = projects.filter(transaction_amount__gte=1000, transaction_amount__lt=5000)
    elif amount_filter == '5000-inf':
        projects = projects.filter(transaction_amount__gte=5000)

    # Default ordering if needed, maybe by time desc
    projects = projects.order_by('-procurement_time')

    return render(request, 'reports/partials/project_table.html', {
        'projects': projects
    })

def filter_ongoing_projects(request, report_id):
    report = get_object_or_404(ReportPage, id=report_id)
    projects = OngoingProject.objects.filter(page=report)

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        projects = projects.filter(
            Q(project_name__icontains=q) |
            Q(procurement_unit__icontains=q)
        )

    # 2. Time Filter (bid_opening_time)
    time_filter = request.GET.get('time', 'all')
    now = timezone.now().date()
    # 1m, 3m, 6m, 1y, 3y
    if time_filter == '1m':
        limit = now - timedelta(days=30)
        projects = projects.filter(bid_opening_time__gte=limit)
    elif time_filter == '3m':
        limit = now - timedelta(days=90)
        projects = projects.filter(bid_opening_time__gte=limit)
    elif time_filter == '6m':
        limit = now - timedelta(days=180)
        projects = projects.filter(bid_opening_time__gte=limit)
    elif time_filter == '1y':
        limit = now - timedelta(days=365)
        projects = projects.filter(bid_opening_time__gte=limit)
    elif time_filter == '3y':
        limit = now - timedelta(days=365*3)
        projects = projects.filter(bid_opening_time__gte=limit)

    # 3. Amount Filter (budget_amount)
    amount_filter = request.GET.get('amount', 'all')
    if amount_filter != 'all':
        try:
            if amount_filter == '5000-inf':
                projects = projects.filter(budget_amount__gte=5000)
            else:
                min_val, max_val = map(float, amount_filter.split('-'))
                projects = projects.filter(budget_amount__gte=min_val, budget_amount__lte=max_val)
        except ValueError:
            pass
            
    context = {
        'projects': projects,
    }
    return render(request, 'reports/partials/ongoing_project_table.html', context)


def filter_purchase_intentions(request, report_id):
    report = get_object_or_404(ReportPage, id=report_id)
    intentions = report.purchase_intentions.all()

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        intentions = intentions.filter(
            Q(project_name__icontains=q) |
            Q(procurement_unit__icontains=q) |
            Q(content__icontains=q)
        )

    # 2. Amount Filter (Budget)
    # 2. Amount Filter (Budget)
    amount_filter = request.GET.get('amount', 'all')
    if amount_filter != 'all':
        try:
            if amount_filter == '5000-inf':
                intentions = intentions.filter(budget_amount__gte=5000)
            else:
                # Expect format 'min-max' e.g. '0-10', '10-50'
                min_val, max_val = map(float, amount_filter.split('-'))
                intentions = intentions.filter(budget_amount__gte=min_val, budget_amount__lt=max_val)
        except ValueError:
            pass

    # 3. Region Filter (Province)
    region_filter = request.GET.get('region', 'All')
    if region_filter and region_filter not in ['All', '全国']:
        # Map frontend "region" values to model "province" values if needed
        # Assuming frontend passes full province names like "四川"
        intentions = intentions.filter(province__icontains=region_filter)

    context = {
        'intentions': intentions,
    }
    return render(request, 'reports/partials/intention_list.html', context)


def filter_announcements(request, report_id):
    report = get_object_or_404(ReportPage, id=report_id)
    announcements = report.report_announcements.all()

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        announcements = announcements.filter(
            Q(title__icontains=q) |
            Q(buyer__icontains=q)
        )

    # 2. Time Filter
    time_filter = request.GET.get('time', 'all')
    now = timezone.now().date()
    if time_filter == '1m':
        limit = now - timedelta(days=30)
        announcements = announcements.filter(publish_date__gte=limit)
    elif time_filter == '3m':
        limit = now - timedelta(days=90)
        announcements = announcements.filter(publish_date__gte=limit)
    elif time_filter == '6m':
        limit = now - timedelta(days=180)
        announcements = announcements.filter(publish_date__gte=limit)
    elif time_filter == '1y':
        limit = now - timedelta(days=365)
        announcements = announcements.filter(publish_date__gte=limit)
    elif time_filter == '3y':
        limit = now - timedelta(days=365*3)
        announcements = announcements.filter(publish_date__gte=limit)

    # 3. Amount Filter (Budget or Transaction - checking budget first, fallback to transaction?)
    # Requirement says "Project Amount". Let's filter on budget_amount.
    amount_filter = request.GET.get('amount', 'all')
    if amount_filter != 'all':
        try:
            if amount_filter == '5000-inf':
                announcements = announcements.filter(budget_amount__gte=5000)
            else:
                min_val, max_val = map(float, amount_filter.split('-'))
                announcements = announcements.filter(budget_amount__gte=min_val, budget_amount__lt=max_val)
        except ValueError:
            pass

    # 4. Region Filter
    region_filter = request.GET.get('region', 'All')
    if region_filter and region_filter not in ['All', '全国']:
        announcements = announcements.filter(region__icontains=region_filter)

    # 5. Type Filter
    type_filter = request.GET.get('type', 'all')
    if type_filter and type_filter != 'all':
         # Map frontend text to choice keys if needed, or use keys directly.
         # Assuming frontend passes keys like 'bidding', 'result', etc.
         announcements = announcements.filter(announcement_type=type_filter)

    context = {
        'announcements': announcements,
    }
    return render(request, 'reports/partials/announcement_table.html', context)


def filter_contracts(request, report_id):
    report = get_object_or_404(ReportPage, id=report_id)
    contracts = report.report_contracts.all()

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        contracts = contracts.filter(
            Q(title__icontains=q) |
            Q(buyer__icontains=q)
        )

    # 2. Time Filter
    time_filter = request.GET.get('time', 'all')
    now = timezone.now().date()
    if time_filter == '1m':
        limit = now - timedelta(days=30)
        contracts = contracts.filter(publish_date__gte=limit)
    elif time_filter == '3m':
        limit = now - timedelta(days=90)
        contracts = contracts.filter(publish_date__gte=limit)
    elif time_filter == '6m':
        limit = now - timedelta(days=180)
        contracts = contracts.filter(publish_date__gte=limit)
    elif time_filter == '1y':
        limit = now - timedelta(days=365)
        contracts = contracts.filter(publish_date__gte=limit)
    elif time_filter == '3y':
        limit = now - timedelta(days=365*3)
        contracts = contracts.filter(publish_date__gte=limit)

    # 3. Amount Filter (Budget Amount)
    amount_filter = request.GET.get('amount', 'all')
    if amount_filter != 'all':
        try:
            if amount_filter == '5000-inf':
                contracts = contracts.filter(budget_amount__gte=5000)
            else:
                min_val, max_val = map(float, amount_filter.split('-'))
                contracts = contracts.filter(budget_amount__gte=min_val, budget_amount__lt=max_val)
        except ValueError:
            pass

    # 4. Region Filter
    region_filter = request.GET.get('region', 'All')
    if region_filter and region_filter not in ['All', '全国']:
        contracts = contracts.filter(region__icontains=region_filter)

    context = {
        'contracts': contracts,
    }
    return render(request, 'reports/partials/contract_table.html', context)


def filter_documents(request, report_id):
    report = get_object_or_404(ReportPage, id=report_id)
    documents = report.report_documents.all()

    # 1. Search Query (Title)
    q = request.GET.get('q', '').strip()
    if q:
        documents = documents.filter(title__icontains=q)
        
    # 2. Type Filter (procurement, contract, acceptance)
    doc_type = request.GET.get('type', 'all')
    if doc_type and doc_type != 'all' and doc_type != 'All':
         documents = documents.filter(doc_type=doc_type)

    # 3. File Format Filter (auto-detect from file extension)
    file_format = request.GET.get('format', 'all').strip().lower()
    if file_format and file_format != 'all':
        documents = documents.filter(file__endswith='.' + file_format)

    # Order by upload time desc
    documents = documents.order_by('-upload_time')

    context = {
        'documents': documents,
    }
    return render(request, 'reports/partials/document_table.html', context)

