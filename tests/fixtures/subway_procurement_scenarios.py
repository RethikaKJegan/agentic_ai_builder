"""Deterministic modeled Subway scenarios. Never imported by production modules."""
from copy import deepcopy

AS_OF='2026-11-12T12:00:00+05:30'


def generate(name='standard'):
    e={
      'purchaseorders':[dict(_id=1001,poNumber='SCENARIO-PO-1001',poDate='2026-10-01T00:00:00Z',createdAt='2026-10-01T00:00:00Z',status='approved',
        vendorCode='SCENARIO-SUP-1',vendorName='Modeled bakery supplier',currency=1,site=10,budget=20,financialYear='2026-27',amount=1000,totalAmount=1180,
        approvalId=501,purchaseRequestId=901,items=[dict(_id='SCENARIO-LINE-1',item=101,lineItem=30,quantity=10,rate=100,amount=1000,taxAmount=180,totalAmount=1180,uom='NOS')])],
      'purchaserequests':[dict(_id=901,prNumber='SCENARIO-PR-901',prDate='2026-09-25T00:00:00Z',prScope='SINGLE_STORE',prType='OPEX',site=10,createdBy=90,status='approved',approvalId=502,isParentPR=False,legacyAllocationUnresolved=False,items=[dict(_id='SCENARIO-PR-L1',item=101,quantity=10)])],
      'approvals':[dict(_id=501,status='approved',approvalType='po_approval',createdAt='2026-10-01T00:00:00Z',stages=[601,602]),dict(_id=502,status='approved',approvalType='pr_approval',createdAt='2026-09-25T00:00:00Z',stages=[603])],
      'stages':[dict(_id=601,approvalId=501,status='approved',StageNumber=1,stageDate='2026-10-02T00:00:00Z'),dict(_id=602,approvalId=501,status='approved',StageNumber=2,stageDate='2026-10-03T00:00:00Z'),dict(_id=603,approvalId=502,status='approved',StageNumber=1)],
      'grns':[dict(_id=701,grnNo='SCENARIO-GRN-701',purchaseOrderId=1001,status='approved',inwardDate='2026-10-05T00:00:00Z',invoiceDate='2026-10-05T00:00:00Z',invoiceNumber='SCENARIO-INV-801',receivedItems=[dict(_id='SCENARIO-R1',poItemId='SCENARIO-LINE-1',receivedQuantity=4)]),dict(_id=702,grnNo='SCENARIO-GRN-702',purchaseOrderId=1001,status='approved',inwardDate='2026-10-06T00:00:00Z',invoiceDate='2026-10-06T00:00:00Z',invoiceNumber='SCENARIO-INV-801',receivedItems=[dict(_id='SCENARIO-R2',poItemId='SCENARIO-LINE-1',receivedQuantity=6)])],
      # Currency/full-order scope below are modeled supplemental evidence. They
      # are deliberately absent from the production projection of invoice data.
      'invoicedatas':[dict(_id=801,invoiceNumber='SCENARIO-INV-801',invoiceDate='2026-10-06T00:00:00Z',invoiceAmount=1180,poId=1001,grnId=701,vendorCode='SCENARIO-SUP-1',financialYear='2026-27',currency=1,coversFullOrder=True,status='created')],
      'lineitems':[dict(_id=30,budgetId=20,availableAmount=5000,reservedAmount=1180,currentAmount=10000,initialAmount=10000,financialYear='2026-27',currency=1)],
      'budgets':[dict(_id=20,site=10,financialYear='2026-27',utilizedAmount=5000,status='approved')],
      'items':[dict(_id=101,itemCode='SCENARIO-ITEM-101',name='Modeled packaging carton',uom='NOS')],
      'locations':[dict(_id=10,code='SCENARIO-LOC-10',name='Modeled finance location')],
    }
    if name=='partial':e['grns'].pop()
    elif name=='over_received':e['grns'][1]['receivedItems'][0]['receivedQuantity']=7
    elif name=='duplicate_invoice':e['invoicedatas'].append(dict(e['invoicedatas'][0],_id=802))
    elif name=='budget_overrun':e['lineitems'][0]['availableAmount']=100
    elif name=='missing_evidence':
        e['purchaseorders'][0].pop('purchaseRequestId');e['lineitems'][0].pop('reservedAmount');e['approvals']=[]
        e['invoicedatas'][0].pop('currency');e['invoicedatas'][0].pop('coversFullOrder')
    elif name in ('in_progress','rejected','reconsider','cancelled','inconsistent_history'):
        st='approved' if name=='inconsistent_history' else 'approval_in_progress' if name=='in_progress' else name
        e['approvals'][0]['status']=st
        if name=='inconsistent_history':e['approvals'][0]['approved']=False
        e['stages'][1]['status']='approval_in_progress' if name=='inconsistent_history' else st
        e['purchaseorders'][0]['status']=st
    elif name=='missing_relationship':e['grns'][0]['purchaseOrderId']=9999
    elif name=='duplicate_line':e['purchaseorders'][0]['items'].append(deepcopy(e['purchaseorders'][0]['items'][0]))
    elif name=='currency_mismatch':e['invoicedatas'][0]['currency']=2
    elif name=='modeled_cross_source_mapping':
        e['central_stores']=[dict(_id=2001,restaurantName='Modeled restaurant') ]
        e['central_vendors']=[dict(_id=3001,name='Modeled bakery supplier',splCode='SCENARIO-SUP-1')]
        e['scenario_correspondences']=[
            dict(_id='SCENARIO-STORE-MAP',source_dataset='central.stores',source_id=2001,target_dataset='finance.locations',target_id=10,origin='modeled_test_fixture',authoritative=False),
            dict(_id='SCENARIO-VENDOR-MAP',source_dataset='central.vendors',source_id=3001,target_dataset='finance.purchaseorders.vendorCode',target_id='SCENARIO-SUP-1',origin='modeled_test_fixture',authoritative=False)]
    elif name=='invalid_amount':e['purchaseorders'][0]['amount']=-5
    elif name!='standard':raise ValueError(name)
    return dict(scenario_version='subway-procurement-scenarios-v1',name=name,origin='modeled_test_fixture',authoritative=False,evidence=e)

SCENARIOS=['standard','partial','over_received','duplicate_invoice','budget_overrun','missing_evidence','in_progress','rejected','reconsider','cancelled','inconsistent_history','missing_relationship','duplicate_line','currency_mismatch','invalid_amount','modeled_cross_source_mapping']
