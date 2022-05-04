function main() {
  const dataReq = fetch('./api/all-exchanges.txt')
    .then(res => res.text())
    .then(data => {
      const body = document.querySelector('body');
      body.innerHTML = data.replaceAll("\n", "<br/>")
    });
}

document.addEventListener('DOMContentLoaded', (_) => {
  main();
});
