"""Deterministic persistent-demo authoring. These are modeled records, never company observations."""
from copy import deepcopy
from hashlib import sha256
from .business_knowledge_model import digest

DATASET='subway-demonstration-v1'
VERSION='bov_subway_demonstration_v1'
SCOPE=('client-subway','subway-client')
LABEL='MODELED SUBWAY DEMONSTRATION — generated records and illustrative policies; not actual Subway operations or official company policy.'
POLICY=dict(id='subway-demo-policy-v1',revision=1,authority='modeled_demonstration_only',invoice_absolute_tolerance='5.00',approval_second_stage_above='5000.00',approval_delay_days=7,as_of='2026-11-12T12:00:00+05:30',currency_conversion=False)


def generate():
    records={k:[] for k in ['central.stores','central.vendors','finance.locations','finance.storemappings','finance.suppliermappings','finance.items','finance.budgets','finance.lineitems','finance.purchaserequests','finance.purchaseorders','finance.approvals','finance.stages','finance.grns','finance.invoicedatas','finance.invoiceitems','finance.payments','finance.reservations','finance.allocations']}
    def add(dataset,**row):
        row['demo_origin']='modeled_demonstration';row['demo_dataset']=DATASET
        records[dataset].append(row);return row
    for i in range(1,5):
        add('central.stores',_id=2000+i,restaurantName=f'Demo Restaurant {i}',storeCode=f'DEMO-STORE-{i:02}',city=['Chennai','Bengaluru','Hyderabad','Mumbai'][i-1])
        add('finance.locations',_id=100+i,storeId=2000+i,name=f'Demo Finance Location {i}',code=f'DEMO-LOC-{i:02}',currency=1,region='Demo India')
        add('finance.storemappings',_id=i,centralStoreId=2000+i,financeLocationId=100+i,mappingBasis='explicit modeled correspondence')
        add('finance.budgets',_id=300+i,site=100+i,financialYear='DEMO-2026',currency=1,initialAmount=40000,modifiedBudgetCost=40000,utilizedAmount=6000,reservedAmount=4000,availableBudgetCost=30000,status='approved')
    for i in range(1,4):
        add('central.vendors',_id=400+i,name=f'Demo Supplier {i}',splCode=f'DEMO-SUP-{i:02}')
        add('finance.suppliermappings',_id=i,centralVendorId=400+i,vendorCode=f'DEMO-SUP-{i:02}',mappingBasis='explicit modeled supplier correspondence')
    for i in range(1,9):
        loc=101+(i-1)%4;vendor=401+(i-1)%3;currency=1 if i<=6 else 2;pid=1000+i;rid=2000+i;inv=3000+i;budget=300+i;line=500+i
        qty=10;rate=100+i*10;net=qty*rate*2;tax=net*18//100;gross=net+tax
        add('finance.items',_id=600+i,name=f'Demo Packaging Item {i}',itemCode=f'DEMO-ITEM-{i:02}',uom='NOS',price=rate)
        if i>4:add('finance.budgets',_id=budget,site=loc,financialYear='DEMO-2026',currency=currency,initialAmount=40000,modifiedBudgetCost=40000,utilizedAmount=6000,openingUtilizedAmount=6000,status='approved')
        b=next(b for b in records['finance.budgets'] if b['_id']==budget);b.update(currency=currency,reservedAmount=gross,availableBudgetCost=40000-6000-gross,openingUtilizedAmount=6000)
        add('finance.lineitems',_id=line,budgetId=budget,name=f'Demo allocation {i}',initialAmount=10000,currentAmount=10000,availableAmount=100 if i==4 else 10000-gross-500,recordedExpenditure=10000-gross-100 if i==4 else 500,reservedAmount=gross,currency=currency,financialYear='DEMO-2026',status='approved')
        approval_status='approval_in_progress' if i in (5,8) else 'rejected' if i==6 else 'approved'
        poitems=[dict(_id=f'DEMO-PO-{i}-LINE-{j}',item=600+i,lineItem=line,quantity=qty,rate=rate,amount=qty*rate,taxAmount=qty*rate*18//100,totalAmount=qty*rate*118//100,uom='NOS',prItemId=f'DEMO-PR-{i}-LINE-{j}') for j in (1,2)]
        add('finance.purchaseorders',_id=pid,poNumber=f'DEMO-PO-{i:03}',poDate=f'2026-11-{i:02}T04:30:00Z',createdAt=f'2026-11-{i:02}T04:30:00Z',status=approval_status,
            vendorId=vendor,vendorCode=f'DEMO-SUP-{vendor-400:02}',vendorName=f'Demo Supplier {vendor-400}',site=loc,storeId=2000+loc-100,budget=budget,currency=currency,financialYear='DEMO-2026',
            purchaseRequestId=rid,approvalId=4000+i,amount=net,taxAmount=tax,totalAmount=gross,items=poitems,scenario='budget_overrun' if i==4 else 'invoice_variance' if i==3 else 'partial_receipt' if i==7 else 'missing_stage_evidence' if i==8 else approval_status)
        add('finance.purchaserequests',_id=rid,prNumber=f'DEMO-PR-{i:03}',prDate=f'2026-10-{20+i:02}T04:30:00Z',createdAt=f'2026-10-{20+i:02}T04:30:00Z',prScope='SINGLE_STORE',prType='OPEX',site=loc,createdBy=90+i,status='approved',approvalId=5000+i,isParentPR=False,legacyAllocationUnresolved=False,purchaseOrderIds=[pid],preferredVendorCode=f'DEMO-SUP-{vendor-400:02}',items=[dict(_id=f'DEMO-PR-{i}-LINE-{j}',item=600+i,quantity=qty,lineItem=line) for j in (1,2)])
        for kind,aid,st in [('po_approval',4000+i,approval_status),('pr_approval',5000+i,'approved'),('invoice_approval',6000+i,'approved')]:
            stageids=[aid*10+1,aid*10+2] if not (i==8 and kind=='po_approval') else []
            add('finance.approvals',_id=aid,status=st,approved=st=='approved',rejected=st=='rejected',approvalType=kind,documentId=str(pid if kind=='po_approval' else rid if kind=='pr_approval' else inv),site=loc,stages=stageids,currentStageNumber=2,cycleNumber=1,createdAt='2026-10-25T04:30:00Z',updatedAt='2026-11-01T04:30:00Z')
            for j,sid in enumerate(stageids,1):add('finance.stages',_id=sid,approvalId=aid,status=st,StageNumber=j,approved=st=='approved',createdAt='2026-10-25T04:30:00Z',stageDate='2026-11-01T04:30:00Z',stageName=f'Demo approval stage {j}')
        received=6 if i==7 else 12 if i==3 else qty
        for n in (1,2):
            grnid=7000+i*10+n
            q=received//2 if n==1 else received-received//2
            add('finance.grns',_id=grnid,grnNo=f'DEMO-GRN-{i}-{n}',purchaseOrderId=pid,status='approved',site=loc,currency=currency,vendorCode=f'DEMO-SUP-{vendor-400:02}',inwardDate=f'2026-11-{i+1:02}T04:30:00Z',invoiceDate=f'2026-11-{i+1:02}T04:30:00Z',invoiceNumber=f'DEMO-INV-{i:03}',invoiceDataId=inv,invoiceAmount=gross,receivedItems=[dict(_id=f'DEMO-REC-{i}-{n}-{j}',poItemId=f'DEMO-PO-{i}-LINE-{j}',receivedQuantity=q,uom='NOS') for j in (1,2)])
        invamount=gross+100 if i==3 else gross;pay=invamount if i in (1,2) else invamount//2 if i==7 else 0
        invitems=[dict(_id=f'DEMO-INV-{i}-LINE-{j}',poLineId=f'DEMO-PO-{i}-LINE-{j}',item=600+i,quantity=12 if i==3 else qty,unitPrice=110 if i==3 else rate,uom='NOS',amount=1320 if i==3 else qty*rate,taxRate=20 if i==3 else 18,taxAmount=264 if i==3 else qty*rate*18//100,totalAmount=1584 if i==3 else qty*rate*118//100,currency=currency) for j in (1,2)]
        add('finance.invoicedatas',_id=inv,invoiceNumber=f'DEMO-INV-{i:03}',invoiceDate=f'2026-11-{i+1:02}T04:30:00Z',dueDate='2026-11-05T04:30:00Z' if i==3 else '2026-11-25T04:30:00Z',invoiceAmount=invamount,currency=currency,coversFullOrder=True,poId=pid,grnId=7000+i*10+1,approvalId=6000+i,vendorCode=f'DEMO-SUP-{vendor-400:02}',financialYear='DEMO-2026',status='approved',paymentStatus='paid' if pay==invamount else 'part_paid' if pay else 'unpaid',paymentAmount=pay,dateOfPayment='2026-11-10T04:30:00Z' if pay else None,items=invitems)
        for item in invitems:add('finance.invoiceitems',**deepcopy(item),invoiceId=inv,poId=pid)
        add('finance.payments',_id=8000+i,invoiceId=inv,poId=pid,currency=currency,amount=pay,paymentDate='2026-11-10T04:30:00Z' if pay else None,paymentStatus='paid' if pay else 'not_paid',reference=f'DEMO-PAY-{i:03}')
        add('finance.reservations',_id=9000+i,purchaseRequestId=rid,purchaseOrderId=pid,lineItemId=line,budgetId=budget,amount=gross,currency=currency,status='reserved',createdAt='2026-10-25T04:30:00Z')
        add('finance.allocations',_id=10000+i,budgetId=budget,lineItemId=line,site=loc,amount=10000,currency=currency,period='DEMO-2026')
    document=dict(dataset_id=DATASET,revision=1,scope=dict(workspace_id=SCOPE[0],owner_id=SCOPE[1]),label=LABEL,mode='modeled_demonstration',as_of=POLICY['as_of'],policy=POLICY,records=records)
    document['sha256']=digest(document)
    return document
