// Converts the mic's 32-bit float samples to 16-bit PCM — what Deepgram's
// linear16 streaming STT expects. Runs on the audio thread.
class PCMProcessor extends AudioWorkletProcessor {
    process(inputs) {
        const ch = inputs[0][0];
        if (!ch) return true;
        const out = new Int16Array(ch.length);
        for (let i = 0; i < ch.length; i++) {
            const s = Math.max(-1, Math.min(1, ch[i]));
            out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        this.port.postMessage(out.buffer, [out.buffer]);
        return true;
    }
}
registerProcessor('pcm-processor', PCMProcessor);