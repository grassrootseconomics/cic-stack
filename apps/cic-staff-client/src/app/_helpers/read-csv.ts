/** An object defining the properties of the data read. */
const objCsv: { size: number; dataFile: any } = {
  size: 0,
  dataFile: [],
};

/**
 * Parses data to CSV format.
 *
 * @param data - The data to be parsed.
 * @returns An array of the parsed data.
 */
function parseData(data: any): Array<any> {
  const csvData: Array<any> = [];
  const lineBreak: Array<any> = data.split('\n');
  lineBreak.forEach((res) => {
    csvData.push(res.split(','));
  });
  console.table(csvData);
  return csvData;
}

/**
 * Reads a csv file and converts it to an array.
 *
 * @param input - The file to be read.
 * @returns An array of the read data.
 */
function readCsv(input: any): Array<any> | void {
  if (input.files && input.files[0]) {
    const reader: FileReader = new FileReader();
    reader.readAsBinaryString(input.files[0]);
    reader.onload = (event) => {
      objCsv.size = event.total;
      objCsv.dataFile = event.target.result;
      return parseData(objCsv.dataFile);
    };
  }
}

/** @exports */
export { readCsv };
