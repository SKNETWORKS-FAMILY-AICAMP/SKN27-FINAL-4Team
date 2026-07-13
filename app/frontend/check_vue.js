const fs = require('fs');
const path = require('path');
const compiler = require(path.join(__dirname, 'node_modules', '@vue', 'compiler-sfc'));

const filename = 'C:\\Dev\\project\\SKN27-FINAL-4Team\\app\\frontend\\src\\views\\mypage\\components\\ProfilePanel.vue';
const content = fs.readFileSync(filename, 'utf-8');

const parsed = compiler.parse(content);
if (parsed.errors.length > 0) {
    console.log("ERRORS:");
    parsed.errors.forEach(e => console.log(e));
} else {
    console.log("No SFC parsing errors!");
}
