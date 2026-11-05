export function getJstSelection(timestamp) {
 const date = new Date(timestamp + 9 * 60 * 60 * 1000);
 return {
  date: date.toISOString().slice(0,10),
  slot: Math.min(46,date.getUTCHours()*2+Math.floor(date.getUTCMinutes()/30))
 };
}
