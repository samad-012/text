"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Mic, Square, Radio, MessageSquare } from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";
const WS_BASE = "ws://127.0.0.1:8000";

type ToolEvent = {
  tool: string;
  arguments?: unknown;
  result?: unknown;
};

type Mode = "turn" | "stream";

export default function Home() {
  const [mode, setMode] = useState<Mode>("turn");
  const [sessionId, setSessionId] = useState<string>("");
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const [transcript, setTranscript] = useState("");
  const [reply, setReply] = useState("");
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([]);

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const playbackQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);

  useEffect(() => {
    setSessionId(crypto.randomUUID());
  }, []);

  async function startRecording() {
    setConnectionError(null);

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });

    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());

      const blob = new Blob(chunksRef.current, {
        type: "audio/webm",
      });

      void sendTurn(blob);
    };

    mediaRecorderRef.current = recorder;
    recorder.start();
    setIsRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }

  async function sendTurn(blob: Blob) {
    setIsProcessing(true);

    const form = new FormData();
    form.append("audio", blob, "clip.webm");
    form.append("session_id", sessionId);

    try {
      const response = await fetch(`${API_BASE}/api/turn`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = await response.json();

      setTranscript(data.transcript);
      setReply(data.reply);

      setToolEvents(
        (data.tool_calls ?? []).map(
          (tc: {
            tool: string;
            arguments: unknown;
            result: unknown;
          }) => ({
            tool: tc.tool,
            arguments: tc.arguments,
            result: tc.result,
          })
        )
      );

      if (data.audio_base64) {
        const audio = new Audio(
          `data:audio/mp3;base64,${data.audio_base64}`
        );

        void audio.play();
      }
    } catch (err) {
      setConnectionError(
        `Couldn't reach the backend at ${API_BASE}. Is uvicorn running? (${err instanceof Error ? err.message : String(err)
        })`
      );
    } finally {
      setIsProcessing(false);
    }
  }

  async function startStreaming() {
    setConnectionError(null);
    setToolEvents([]);
    setTranscript("");
    setReply("");

    const audioCtx = new AudioContext({
      sampleRate: 16000,
    });

    audioCtxRef.current = audioCtx;

    await audioCtx.audioWorklet.addModule(
      "/worklets/pcm-processor.js"
    );

    const micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        channelCount: 1,
      },
    });

    const source = audioCtx.createMediaStreamSource(micStream);

    const workletNode = new AudioWorkletNode(
      audioCtx,
      "pcm-processor"
    );

    source.connect(workletNode);

    const ws = new WebSocket(
      `${WS_BASE}/ws/stream?session_id=${sessionId}`
    );

    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      setIsStreaming(true);

      workletNode.port.onmessage = (
        evt: MessageEvent<ArrayBuffer>
      ) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(evt.data);
        }
      };
    };

    ws.onerror = () => {
      setConnectionError(
        `Couldn't reach ${WS_BASE}/ws/stream. Is the backend running and is the streaming router mounted in app/main.py?`
      );

      stopStreaming();
    };

    ws.onclose = () => {
      setIsStreaming(false);
    };

    ws.onmessage = (evt) => {
      if (evt.data instanceof ArrayBuffer) {
        enqueueAudio(evt.data);
        return;
      }

      const msg = JSON.parse(evt.data);

      switch (msg.type) {
        case "interim":
          setTranscript(msg.text);
          break;

        case "text_delta":
          setReply((prev) => prev + msg.content);
          break;

        case "tool_call":
          setToolEvents((prev) => [
            ...prev,
            {
              tool: msg.tool,
              arguments: msg.arguments,
            },
          ]);
          break;

        case "tool_result":
          setToolEvents((prev) => {
            const next = [...prev];

            for (let i = next.length - 1; i >= 0; i--) {
              if (
                next[i].tool === msg.tool &&
                next[i].result === undefined
              ) {
                next[i] = {
                  ...next[i],
                  result: msg.result,
                };

                break;
              }
            }

            return next;
          });

          break;

        case "barge_in":
          flushPlayback();
          break;

        case "turn_done":
          break;
      }
    };
  }

  function stopStreaming() {
    wsRef.current?.close();
    wsRef.current = null;

    audioCtxRef.current?.close();
    audioCtxRef.current = null;

    playbackQueueRef.current = [];

    setIsStreaming(false);
  }

  function enqueueAudio(buf: ArrayBuffer) {
    playbackQueueRef.current.push(buf);

    if (!isPlayingRef.current) {
      void drainQueue();
    }
  }

  async function drainQueue() {
    isPlayingRef.current = true;

    const ctx = audioCtxRef.current;

    while (
      ctx &&
      playbackQueueRef.current.length > 0
    ) {
      const buf = playbackQueueRef.current.shift()!;

      try {
        const decoded = await ctx.decodeAudioData(
          buf.slice(0)
        );

        await new Promise<void>((resolve) => {
          const src = ctx.createBufferSource();

          src.buffer = decoded;
          src.connect(ctx.destination);

          src.onended = () => resolve();
          src.start();

          currentSourceRef.current = src;
        });
      } catch { }
    }

    isPlayingRef.current = false;
  }

  function flushPlayback() {
    playbackQueueRef.current = [];

    try {
      currentSourceRef.current?.stop();
    } catch { }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-8">
      <h1 className="text-2xl font-semibold">
        Saffron & Ember — Voice Agent
      </h1>

      <div className="flex gap-2">
        <Button
          variant={
            mode === "turn" ? "default" : "outline"
          }
          onClick={() => setMode("turn")}
        >
          <MessageSquare className="mr-2 h-4 w-4" />
          Turn-based
        </Button>

        <Button
          variant={
            mode === "stream" ? "default" : "outline"
          }
          onClick={() => setMode("stream")}
        >
          <Radio className="mr-2 h-4 w-4" />
          Streaming
        </Button>
      </div>

      {connectionError && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          {connectionError}
        </div>
      )}

      {mode === "turn" && (
        <div className="flex flex-col gap-4">
          <Button
            onClick={
              isRecording
                ? stopRecording
                : startRecording
            }
            disabled={isProcessing}
            variant={
              isRecording
                ? "destructive"
                : "default"
            }
          >
            {isRecording ? (
              <Square className="mr-2 h-4 w-4" />
            ) : (
              <Mic className="mr-2 h-4 w-4" />
            )}

            {isRecording
              ? "Stop"
              : isProcessing
                ? "Processing..."
                : "Record"}
          </Button>
        </div>
      )}

      {mode === "stream" && (
        <div className="flex flex-col gap-4">
          <Button
            onClick={
              isStreaming
                ? stopStreaming
                : startStreaming
            }
            variant={
              isStreaming
                ? "destructive"
                : "default"
            }
          >
            {isStreaming ? (
              <Square className="mr-2 h-4 w-4" />
            ) : (
              <Radio className="mr-2 h-4 w-4" />
            )}

            {isStreaming
              ? "Stop"
              : "Start streaming"}
          </Button>
        </div>
      )}

      <div className="flex flex-col gap-1 rounded-md border p-4 text-sm">
        <div>
          <span className="font-medium">
            Transcript:{" "}
          </span>

          {transcript || (
            <span className="text-neutral-400">
              —
            </span>
          )}
        </div>

        <div>
          <span className="font-medium">
            Reply:{" "}
          </span>

          {reply || (
            <span className="text-neutral-400">
              —
            </span>
          )}
        </div>
      </div>

      {toolEvents.length > 0 && (
        <div className="flex flex-col gap-2 rounded-md border p-4 text-xs">
          <span className="font-medium text-sm">
            Tool trace
          </span>

          {toolEvents.map((event, i) => (
            <pre
              key={i}
              className="overflow-x-auto rounded bg-neutral-100 p-2"
            >
              {event.tool}(
              {JSON.stringify(event.arguments)}) →{" "}
              {JSON.stringify(event.result)}
            </pre>
          ))}
        </div>
      )}
    </main>
  );
}