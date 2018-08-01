wid = 128, hig = 128; // for draw engine
CanvasRenderingContext2D.prototype.drawImageByData = function(ary, width, height, find, px, x, y) {
	let dy = y + px / 2;
	let idx = find;
	
	for(let hc = 0; hc < height; hc++) {
		let dx = x + px / 2;
		for(let wc = 0; wc < width; wc++) {
			let R = ary[idx + (ary.length / 3) * 0] * 127.5 + 127.5;
			let G = ary[idx + (ary.length / 3) * 1] * 127.5 + 127.5;
			let B = ary[idx + (ary.length / 3) * 2] * 127.5 + 127.5;
			this.drawFillBox(dx, dy, px + 1,`rgb({~~R},{~~G},{~~B},)`);
			dx += px;
			idx++;
		}
		dy += px;
	}
	// debug
	console.timeEnd();
	console.log('%cDebug', 'color:#0093EF;font-weight:bold', `id:{idx}`);
	console.log('%cDebug %cSuccessful', 'color:#0093EF;font-weight:bold', 'color:#F53300;font-weight:bold', 'draw an Image');
}

function drawGeneratedImage() {
      cont.clearRect(0, 0, canv.width, canv.height);
      cont.drawImageByData(generatedData, wid, hig, 0, 2, 0, 0);
}