class CsvStreamer {
  private queue: any[] = [];
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private decoder = new TextDecoder("utf-8");
  private remainder = ""; // Buffer for split lines across chunks
  private headers: string[] | null = null;
  public complete = false;

  constructor(private url: string) {}

  async start() {
    try {
      const response = await fetch(this.url);
      if (!response.body) throw new Error("ReadableStream not supported");
      
      this.reader = response.body.getReader();
      this.readLoop(); // Start reading in the background
    } catch (e) {
      console.error("Error starting stream:", e);
    }
  }

  private async readLoop() {
    if (!this.reader) return;

    while (true) {
      // 1. Read a chunk (usually a few KB)
      const { done, value } = await this.reader.read();
      
      if (done) {
        this.complete = true;
        // Process any remaining text in the buffer
        if (this.remainder.trim()) this.processChunk(this.remainder, true);
        break;
      }

      // 2. Decode and append to buffer
      const chunk = this.decoder.decode(value, { stream: true });
      this.processChunk(this.remainder + chunk, false);
    }
  }

  private processChunk(text: string, isFinal: boolean) {
    // 3. Split by newline
    const lines = text.split(/\r?\n/);

    // 4. Save the last incomplete line for the next chunk (unless we are done)
    this.remainder = isFinal ? "" : lines.pop() || "";

    for (const line of lines) {
      if (!line.trim()) continue; // Skip empty lines

      if (!this.headers) {
        // First line is headers
        this.headers = line.split(",");
      } else {
        // Parse row to object
        const values = line.split(",");
        const obj: any = {};
        this.headers.forEach((h, i) => {
            obj[h.trim()] = values[i]?.trim();
        });
        this.queue.push(obj);
      }
    }
  }

  // 5. Public method to get the next available line
  public getNextLine() {
    return this.queue.shift() || null;
  }
}
export { CsvStreamer };