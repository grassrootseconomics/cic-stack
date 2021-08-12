/**
 * Exports data to a CSV format and provides a download file.
 *
 * @param arrayData - An array of data to be converted to CSV format.
 * @param filename - The name of the file to be downloaded.
 * @param delimiter - The delimiter to be used when converting to CSV format.
 * Defaults to commas.
 */
function exportCsv(arrayData: Array<any>, filename: string, delimiter: string = ','): void {
  if (arrayData === undefined || arrayData.length === 0) {
    alert('No data to be exported!');
    return;
  }
  let csv: string = Object.keys(arrayData[0]).join(delimiter) + '\n';
  arrayData.forEach((obj) => {
    const row: Array<any> = [];
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        row.push(obj[key]);
      }
    }
    csv += row.join(delimiter) + '\n';
  });

  const csvData: Blob = new Blob([csv], { type: 'text/csv' });
  const csvUrl: string = URL.createObjectURL(csvData);

  const downloadLink: HTMLAnchorElement = document.createElement('a');
  downloadLink.href = csvUrl;
  downloadLink.target = '_blank';
  downloadLink.download = filename + '.csv';
  downloadLink.style.display = 'none';
  document.body.appendChild(downloadLink);
  downloadLink.click();
}

/** @exports */
export { exportCsv };
