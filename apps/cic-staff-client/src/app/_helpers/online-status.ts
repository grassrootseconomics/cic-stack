const apiUrls = [
  'https://api.coindesk.com/v1/bpi/currentprice.json',
  'https://dog.ceo/api/breeds/image/random',
];

async function checkOnlineStatus(): Promise<boolean> {
  try {
    const online = await fetch(apiUrls[Math.floor(Math.random() * apiUrls.length)]);
    return online.status >= 200 && online.status < 300;
  } catch (error) {
    return false;
  }
}

export { checkOnlineStatus };
