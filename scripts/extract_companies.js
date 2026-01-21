// Extract company names from TrueUp pages
// Run this in browser console on pages like:
// https://www.trueup.io/top/fintech
// https://www.trueup.io/top/ai
// https://www.trueup.io/hypergrowth

// For top lists (fintech, ai, etc.)
const fromTopList = [...document.querySelectorAll('div.w-full.truncate')]
  .map(el => el.textContent.trim())
  .filter(name => name.length > 0);

// For hypergrowth/fastest-growing lists
const fromGrowthList = [...document.querySelectorAll('a.font-semibold')]
  .map(el => el.textContent.trim())
  .filter(name => name.length > 0 && !name.includes('http'));

const companies = fromTopList.length > 0 ? fromTopList : fromGrowthList;

console.log(`Found ${companies.length} companies`);
console.log(JSON.stringify(companies, null, 2));
copy(companies);
console.log('Copied to clipboard!');
