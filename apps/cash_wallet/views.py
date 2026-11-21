from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from .forms import CashInflowForm, CashSpendForm
from .models import CashInflow, CashSpend


@login_required
def wallet_dashboard(request):
    inflows = CashInflow.objects.filter(user=request.user)
    spends = CashSpend.objects.filter(user=request.user)

    total_cash_in = inflows.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_cash_spent = spends.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_in_hand = total_cash_in - total_cash_spent

    inflow_form = CashInflowForm()
    spend_form = CashSpendForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_cash':
            inflow_form = CashInflowForm(request.POST)
            if inflow_form.is_valid():
                obj = inflow_form.save(commit=False)
                obj.user = request.user
                obj.save()
                messages.success(request, f"Added ₹{obj.amount} to Cash Wallet.")
                return redirect('cash_wallet:index')
        elif action == 'spend_cash':
            spend_form = CashSpendForm(request.POST)
            if spend_form.is_valid():
                obj = spend_form.save(commit=False)
                obj.user = request.user
                obj.save()
                messages.success(request, f"Logged ₹{obj.amount} cash expense.")
                return redirect('cash_wallet:index')

    context = {
        'total_cash_in': total_cash_in,
        'total_cash_spent': total_cash_spent,
        'cash_in_hand': cash_in_hand,
        'inflows': inflows[:30],
        'spends': spends[:50],
        'inflow_form': inflow_form,
        'spend_form': spend_form,
    }
    return render(request, 'cash_wallet/index.html', context)


@login_required
def delete_inflow(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(CashInflow, pk=pk, user=request.user)
        entry.delete()
        messages.info(request, "Cash inflow entry removed.")
    return redirect('cash_wallet:index')


@login_required
def delete_spend(request, pk):
    if request.method == 'POST':
        entry = get_object_or_404(CashSpend, pk=pk, user=request.user)
        entry.delete()
        messages.info(request, "Cash expense entry removed.")
    return redirect('cash_wallet:index')