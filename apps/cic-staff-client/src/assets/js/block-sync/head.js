const window = self;

self.importScripts('driver.js', 'web3.min.js');

async function sync(driver) {
  driver.hi = driver.lo;
  let getBlockNumber = async function () {
    while (true) {
      const currentBlockNumber = await driver.w3.eth.getBlockNumber();
      if (currentBlockNumber > driver.hi) {
        for (let i = driver.hi + 1; i <= currentBlockNumber; i++) {
          console.log(driver.hi, i, currentBlockNumber);
          driver.w3.eth.getBlock(i).then(async (block) => {
            console.log('current block', block);
            const count = await driver.w3.eth.getBlockTransactionCount(block.number);
            console.log('count', count);
            for (let i = 0; i < count; i++) {
              console.log('driver process ', block.number, i);
              driver.process(block.number, i);
            }
          });
          driver.hi++;
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  };
  await getBlockNumber();
}

onmessage = function (o) {
  const w3 = new Web3(o.data.w3_provider);

  const callback = (o) => {
    this.postMessage(o);
  };

  w3.eth.getBlockNumber().then(async function (blockNumber) {
    const driver = new Driver(w3, blockNumber, undefined, undefined, callback);
    await sync(driver);
  });
};
