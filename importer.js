use('healthcare_db');
const fs = require('fs');

function parseCSV(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split(/\r?\n/).filter(line => line.trim() !== '');
    if (lines.length === 0) return [];

    const headers = lines[0].split(',').map(h => h.trim());
    const docs = [];

    // Robust CSV parser to handle empty columns and quotes
    for (let i = 1; i < lines.length; i++) {
        let row = [];
        let inQuote = false;
        let value = '';
        for (let char of lines[i]) {
            if (inQuote) {
                if (char === '"') inQuote = false;
                else value += char;
            } else {
                if (char === '"') inQuote = true;
                else if (char === ',') {
                    row.push(value.trim());
                    value = '';
                } else {
                    value += char;
                }
            }
        }
        row.push(value.trim());

        const doc = {};
        headers.forEach((header, index) => {
            // Check if header exists to prevent undefined keys
            if (header) {
                doc[header] = row[index] === '' ? null : row[index];
            }
        });
        docs.push(doc);
    }
    return docs;
}

const tables = ['encounters', 'organizations', 'patients', 'payers', 'procedures'];
const csvDirectoryPath = '/absolute/path/to/your/csv/files'; // UPDATE THIS

tables.forEach(collectionName => {
    const filePath = `${csvDirectoryPath}/${collectionName}.csv`;
    if (fs.existsSync(filePath)) {
        const data = parseCSV(filePath);
        if (data.length > 0) {
            db.getCollection(collectionName).drop();
            db.getCollection(collectionName).insertMany(data);
            console.log(`Inserted ${data.length} docs into ${collectionName}`);
        }
    }
});