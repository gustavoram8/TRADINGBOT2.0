export function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    // Next.js 14 throws ResponseAborted as an unhandled rejection when the
    // client closes the connection during a streaming response. Without this
    // handler the Node.js process exits, PM2 restarts it, and the next
    // request hits a cold-starting server. We suppress it here so the process
    // stays alive; the individual request still fails on the client side
    // (browser gets a network error), but no other in-flight requests are
    // affected.
    process.on("unhandledRejection", (reason) => {
      if (
        reason instanceof Error &&
        (reason.message === "ResponseAborted" ||
          reason.message.includes("Response body object should not be disturbed"))
      ) {
        return;
      }
      console.error("[UnhandledRejection]", reason);
    });
  }
}
