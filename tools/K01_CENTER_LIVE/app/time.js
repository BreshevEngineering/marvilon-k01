'use strict';
function kyivTime(input) {
  if (input === null || input === undefined || input === '') return 'Not recorded in source';
  const original = String(input);
  // Do not interpret a timezone-free producer timestamp as this computer's time.
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(original)) return original + ' [source timezone not declared]';
  const date = new Date(original);
  if (Number.isNaN(date.getTime())) return original + ' [invalid timestamp]';
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Europe/Kyiv', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
    }).formatToParts(date);
    const p = Object.fromEntries(parts.map(x => [x.type, x.value]));
    return `${p.day}.${p.month}.${p.year} ${p.hour}:${p.minute}:${p.second} · Kyiv`;
  } catch (_) {
    return original + ' [Kyiv timezone unavailable in this browser]';
  }
}
if (typeof module !== 'undefined') module.exports = { kyivTime };
