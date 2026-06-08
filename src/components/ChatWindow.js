import React, { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import { marked } from "marked";

function ChatWindow() {

  const defaultMessage = {
    role: "assistant",
    content: "Hi, I can help with PartSelect refrigerator and dishwasher parts, troubleshooting, installation, compatibility, and order self-service."
  };

  const [messages,setMessages] = useState([defaultMessage])
  const [input, setInput] = useState("");
  const [currentFlow, setCurrentFlow] = useState(null);
  const [isSending, setIsSending] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
      scrollToBottom();
  }, [messages]);

  const handleSend = async (messageText = input) => {
    if (messageText.trim() !== "" && !isSending) {
      const userMessage = { role: "user", content: messageText };
      const isRestart = ["start over", "restart", "new issue", "forget that"].includes(messageText.trim().toLowerCase());
      const nextMessages = isRestart ? [defaultMessage, userMessage] : [...messages, userMessage];
      setMessages(nextMessages);
      setInput("");
      setIsSending(true);

      try {
        const newMessage = await getAIMessage({
          messages: nextMessages,
          currentFlow: isRestart ? null : currentFlow,
        });
        setCurrentFlow(newMessage.flow || null);
        setMessages(prevMessages => [...prevMessages, newMessage]);
      } catch (error) {
        setMessages(prevMessages => [...prevMessages, {
          role: "assistant",
          content: "I couldn't reach the PartSelect assistant backend. Please make sure the FastAPI server is running on http://localhost:8000."
        }]);
      } finally {
        setIsSending(false);
      }
    }
  };

  return (
      <div className="messages-container">
          {messages.map((message, index) => (
              <div key={index} className={`${message.role}-message-container`}>
                  {message.content && (
                      <div className={`message ${message.role}-message`}>
                          <div dangerouslySetInnerHTML={{__html: marked(message.content).replace(/<p>|<\/p>/g, "")}}></div>
                          {message.sources && message.sources.length > 0 && (
                            <div className="sources">
                              {message.sources.map((source, sourceIndex) => (
                                <a key={sourceIndex} href={source.url} target="_blank" rel="noreferrer">
                                  {source.label}
                                </a>
                              ))}
                            </div>
                          )}
                          {message.suggested_replies && message.suggested_replies.length > 0 && (
                            <div className="suggested-replies">
                              {message.suggested_replies.map((reply, replyIndex) => (
                                <button key={replyIndex} onClick={() => handleSend(reply)}>
                                  {reply}
                                </button>
                              ))}
                            </div>
                          )}
                      </div>
                  )}
              </div>
          ))}
          <div ref={messagesEndRef} />
          <div className="input-area">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              onKeyPress={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  handleSend(input);
                  e.preventDefault();
                }
              }}
              rows="3"
              disabled={isSending}
            />
            <button className="send-button" onClick={() => handleSend(input)} disabled={isSending}>
              {isSending ? "Sending" : "Send"}
            </button>
          </div>
      </div>
);
}

export default ChatWindow;
