var path = require('path');
var fs = require('fs');
var nomnoml = require('nomnoml');

const directoryPath = path.join(__dirname, 'workflow');
const imagesPath = path.join(directoryPath, 'images');

fs.readdir(directoryPath, (err, files) => {
    if (err) {
        return console.log('Unable to scan directory: ' + err);
    }

    files.forEach(file => {
        const filePath = path.join(directoryPath, file);
        fs.readFile(filePath, 'utf-8', (err, data) => {
            if (err) {
                return console.log('Unable to scan file: ' + err);
            }

            const image = nomnoml.renderSvg(data);
            const name = file.split('.')[0];
            fs.writeFile(`${imagesPath}/${name}.svg`, image, (err) => {
                if (err) throw err;
                console.log('Image saved!');
            });
        });
    });
});