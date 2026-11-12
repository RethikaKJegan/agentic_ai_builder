/** Provider receipts establish delivery; content generation never does. */
export function communicationStatuses(instances:Record<string,unknown>|undefined) {
 const entries=Object.values(instances??{}).filter((v):v is Record<string,unknown>=>!!v&&typeof v==='object');
 return entries.flatMap(item=>{
  const capability=String(item['capability_id']??'');const out=item['output'] as Record<string,unknown>|undefined;
  const confirmed=item['state']==='completed'&&item['verified_receipt']===true;
  if(/(?:extension_mail_send|smtp_send_email)$/.test(capability))return [{kind:'email',confirmed,label:confirmed&&!!out?.['message_id']?'Report emailed':item['state']==='failed'?'Email needs attention':'Email pending'}];
  if(/extension_mail_draft$/.test(capability))return [{kind:'email',confirmed,label:confirmed&&!!out?.['draft_id']?'Email draft prepared':'Email draft pending'}];
  if(/extension_calendar_create$/.test(capability))return [{kind:'calendar',confirmed,label:confirmed&&!!out?.['event_id']&&out?.['status']!=='cancelled'?'Review scheduled':['failed','blocked'].includes(String(item['state']))?'Review needs attention':'Review pending'}];
  return [];
 });
}
