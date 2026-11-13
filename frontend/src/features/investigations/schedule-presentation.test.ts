import {it,expect} from 'vitest';
import {scheduleLabel,scheduleDate} from './DurableAutomation';
it('formats only supported cron frequencies and preserves the configured timezone',()=>{
 expect(scheduleLabel({cron:'0 9 * * *',timezone:'Asia/Kolkata'})).toBe('Every day at 09:00 · Asia/Kolkata');
 expect(scheduleLabel({cron:'46 12 * * 1',timezone:'America/New_York'})).toContain('Monday at 12:46 · America/New_York');
 expect(scheduleLabel({cron:'0 9 1 * *',timezone:'UTC'})).toContain('First day of each month');
 expect(scheduleLabel({cron:'*/7 * * * *',timezone:'UTC'})).toContain('Custom schedule');
 expect(scheduleDate(0,'UTC')).toContain('UTC');expect(scheduleDate(undefined,'UTC')).toBe('Not recorded');
});
