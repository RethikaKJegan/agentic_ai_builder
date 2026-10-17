"""Honest configuration checks and explicitly installed read-only provider probes."""
KNOWN={'smtp','google_sheets','google_drive','google_calendar','google_docs','slack','github','open_meteo','open_library','generic_rest','webhook','brevo_smtp','gmail'}


def check(service,provider,auth,mode='configuration'):
    from .service import ApiFailure
    if provider not in KNOWN:raise ApiFailure('INTEGRATION_UNSUPPORTED','This provider is not supported.',400)
    if mode not in {'configuration','connection'}:raise ApiFailure('INVALID_REQUEST','Choose configuration or connection verification.',400)
    service.authorize(auth,'list_tools')
    response=service.registry_adapter.service.list_tools(auth)
    records=[record for record in response['data']['items'] if record['definition']['provider_id']==provider]
    configured=any(record['definition']['availability']=='enabled' and
        (record['credential_configured'] or record['definition']['authentication']['mode']=='none') for record in records)
    probe=getattr(service,'integration_probes',{}).get(provider)
    result={'provider':provider,'configured':configured,'verified':False,'tested':False,'state':'configured' if configured else 'not_configured',
            'live_test_supported':bool(probe),'message':'Server configuration is present. Connectivity and resource access have not been verified.' if configured else 'Configure an enabled provider and its required credentials on the server.'}
    if mode=='connection':
        if 'admin' not in auth.get('roles',[]) or auth.get('decision')!='allow':raise ApiFailure('OPERATION_NOT_AUTHORIZED','An administrator must verify provider connections.',403)
        if not configured:return result
        if not probe:
            result['message']='Live verification is unavailable for this provider. Only server configuration was checked.'
            return result
        try:
            probe()
            result.update(state='verified',verified=True,tested=True,message='Server connection verified with a read-only check. No message or resource was modified.')
        except Exception:
            result.update(state='connection_failed',message='Connection verification failed. Check server credentials, network access and provider availability.')
    return result


def smtp_probe(env,transport=None):
    """Fixed server-owned Gmail destination; AUTH/NOOP only, never MAIL/RCPT/DATA."""
    import smtplib,ssl
    transport=transport or smtplib.SMTP
    def probe():
        if not env.get('GMAIL_SMTP_USER') or not env.get('GMAIL_SMTP_PASSWORD'):raise ValueError('SMTP configuration missing.')
        with transport('smtp.gmail.com',587,timeout=5) as client:
            client.ehlo();client.starttls(context=ssl.create_default_context());client.ehlo()
            client.login(env['GMAIL_SMTP_USER'],env['GMAIL_SMTP_PASSWORD'])
            code,_=client.noop()
            if code!=250:raise ValueError('SMTP did not confirm readiness.')
    return probe
