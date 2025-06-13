import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Copy, CopyCheck, ChevronDown, ChevronRight, Activity, Search, Brain, Pen, TextSearch, Database } from "lucide-react";
import { InputForm } from "@/components/InputForm";
import { Button } from "@/components/ui/button";
import { useState, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  ProcessedEvent,
} from "@/components/ActivityTimeline";

// Markdown component props type from former ReportView
type MdComponentProps = {
  className?: string;
  children?: ReactNode;
  [key: string]: any;
};

// Markdown components (from former ReportView.tsx)
const mdComponents = {
  h1: ({ className, children, ...props }: MdComponentProps) => (
    <h1 className={cn("text-2xl font-bold mt-4 mb-2", className)} {...props}>
      {children}
    </h1>
  ),
  h2: ({ className, children, ...props }: MdComponentProps) => (
    <h2 className={cn("text-xl font-bold mt-3 mb-2", className)} {...props}>
      {children}
    </h2>
  ),
  h3: ({ className, children, ...props }: MdComponentProps) => (
    <h3 className={cn("text-lg font-bold mt-3 mb-1", className)} {...props}>
      {children}
    </h3>
  ),
  p: ({ className, children, ...props }: MdComponentProps) => (
    <p className={cn("mb-3 leading-7", className)} {...props}>
      {children}
    </p>
  ),
  a: ({ className, children, href, ...props }: MdComponentProps) => (
    <Badge className="text-xs mx-0.5">
      <a
        className={cn("text-blue-400 hover:text-blue-300 text-xs", className)}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    </Badge>
  ),
  ul: ({ className, children, ...props }: MdComponentProps) => (
    <ul className={cn("list-disc pl-6 mb-3", className)} {...props}>
      {children}
    </ul>
  ),
  ol: ({ className, children, ...props }: MdComponentProps) => (
    <ol className={cn("list-decimal pl-6 mb-3", className)} {...props}>
      {children}
    </ol>
  ),
  li: ({ className, children, ...props }: MdComponentProps) => (
    <li className={cn("mb-1", className)} {...props}>
      {children}
    </li>
  ),
  blockquote: ({ className, children, ...props }: MdComponentProps) => (
    <blockquote
      className={cn(
        "border-l-4 border-neutral-600 pl-4 italic my-3 text-sm",
        className
      )}
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }: MdComponentProps) => (
    <code
      className={cn(
        "bg-neutral-900 rounded px-1 py-0.5 font-mono text-xs",
        className
      )}
      {...props}
    >
      {children}
    </code>
  ),
  pre: ({ className, children, ...props }: MdComponentProps) => (
    <pre
      className={cn(
        "bg-neutral-900 p-3 rounded-lg overflow-x-auto font-mono text-xs my-3",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  ),
  hr: ({ className, ...props }: MdComponentProps) => (
    <hr className={cn("border-neutral-600 my-4", className)} {...props} />
  ),
  table: ({ className, children, ...props }: MdComponentProps) => (
    <div className="my-3 overflow-x-auto">
      <table className={cn("border-collapse w-full", className)} {...props}>
        {children}
      </table>
    </div>
  ),
  th: ({ className, children, ...props }: MdComponentProps) => (
    <th
      className={cn(
        "border border-neutral-600 px-3 py-2 text-left font-bold",
        className
      )}
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ className, children, ...props }: MdComponentProps) => (
    <td
      className={cn("border border-neutral-600 px-3 py-2", className)}
      {...props}
    >
      {children}
    </td>
  ),
};

// Simple timeline component without extra headers
const SimpleTimeline: React.FC<{ events: ProcessedEvent[]; isLoading: boolean }> = ({ events, isLoading }) => {
  const getEventIcon = (title: string) => {
    if (title.toLowerCase().includes("generating")) {
      return <TextSearch className="h-4 w-4 text-neutral-400" />;
    } else if (title.toLowerCase().includes("reflection")) {
      return <Brain className="h-4 w-4 text-neutral-400" />;
    } else if (title.toLowerCase().includes("knowledge base")) {
      return <Database className="h-4 w-4 text-neutral-400" />;
    } else if (title.toLowerCase().includes("research")) {
      return <Search className="h-4 w-4 text-neutral-400" />;
    } else if (title.toLowerCase().includes("finalizing")) {
      return <Pen className="h-4 w-4 text-neutral-400" />;
    }
    return <Activity className="h-4 w-4 text-neutral-400" />;
  };

  return (
    <div className="p-4 bg-transparent">
      {isLoading && events.length === 0 && (
        <div className="relative pl-8 pb-4">
          <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-600/50" />
          <div className="absolute left-0.5 top-2 h-5 w-5 rounded-full bg-neutral-600/50 flex items-center justify-center ring-4 ring-neutral-800/30">
            <Loader2 className="h-3 w-3 text-neutral-400 animate-spin" />
          </div>
          <div>
            <p className="text-sm text-neutral-300 font-medium">
              Searching...
            </p>
          </div>
        </div>
      )}
      {events.length > 0 && (
        <div className="space-y-0">
          {events.map((eventItem, index) => (
            <div key={index} className="relative pl-8 pb-4">
              {index < events.length - 1 || (isLoading && index === events.length - 1) ? (
                <div className="absolute left-3 top-3.5 h-full w-0.5 bg-neutral-600/50" />
              ) : null}
              <div className="absolute left-0.5 top-2 h-6 w-6 rounded-full bg-neutral-600/50 flex items-center justify-center ring-4 ring-neutral-800/30">
                {getEventIcon(eventItem.title)}
              </div>
              <div>
                <p className="text-sm text-neutral-200 font-medium mb-0.5">
                  {eventItem.title}
                </p>
                <p className="text-xs text-neutral-300 leading-relaxed">
                  {typeof eventItem.data === "string"
                    ? eventItem.data
                    : Array.isArray(eventItem.data)
                    ? (eventItem.data as string[]).join(", ")
                    : JSON.stringify(eventItem.data)}
                </p>
              </div>
            </div>
          ))}
          {isLoading && events.length > 0 && (
            <div className="relative pl-8 pb-4">
              <div className="absolute left-0.5 top-2 h-5 w-5 rounded-full bg-neutral-600/50 flex items-center justify-center ring-4 ring-neutral-800/30">
                <Loader2 className="h-3 w-3 text-neutral-400 animate-spin" />
              </div>
              <div>
                <p className="text-sm text-neutral-300 font-medium">
                  Searching...
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Props for HumanMessageBubble
interface HumanMessageBubbleProps {
  message: Message;
  mdComponents: typeof mdComponents;
}

// HumanMessageBubble Component
const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = ({
  message,
  mdComponents,
}) => {
  return (
    <div
      className={`text-white rounded-3xl break-words min-h-7 bg-neutral-700 max-w-[100%] sm:max-w-[90%] px-4 pt-3 rounded-br-lg`}
    >
      <ReactMarkdown components={mdComponents}>
        {typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content)}
      </ReactMarkdown>
    </div>
  );
};

// Props for AiMessageBubble
interface AiMessageBubbleProps {
  message: Message;
  historicalActivity: ProcessedEvent[] | undefined;
  liveActivity: ProcessedEvent[] | undefined;
  isLastMessage: boolean;
  isOverallLoading: boolean;
  mdComponents: typeof mdComponents;
  handleCopy: (text: string, messageId: string) => void;
  copiedMessageId: string | null;
}

// AiMessageBubble Component
const AiMessageBubble: React.FC<AiMessageBubbleProps> = ({
  message,
  historicalActivity,
  liveActivity,
  isLastMessage,
  isOverallLoading,
  mdComponents,
  handleCopy,
  copiedMessageId,
}) => {
  // Determine which activity events to show and if it's for a live loading message
  const activityForThisBubble =
    isLastMessage && isOverallLoading ? liveActivity : historicalActivity;
  const isLiveActivityForThisBubble = isLastMessage && isOverallLoading;

  return (
    <div className={`relative break-words flex flex-col`}>
      {activityForThisBubble && activityForThisBubble.length > 0 && (
        <div className="mb-3 border-b border-neutral-700 pb-3 text-xs">
          <SimpleTimeline events={activityForThisBubble} isLoading={isLiveActivityForThisBubble} />
        </div>
      )}
      <ReactMarkdown components={mdComponents}>
        {typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content)}
      </ReactMarkdown>
      <Button
        variant="default"
        className="cursor-pointer bg-neutral-700 border-neutral-600 text-neutral-300 self-end"
        onClick={() =>
          handleCopy(
            typeof message.content === "string"
              ? message.content
              : JSON.stringify(message.content),
            message.id!
          )
        }
      >
        {copiedMessageId === message.id ? "Copied" : "Copy"}
        {copiedMessageId === message.id ? <CopyCheck /> : <Copy />}
      </Button>
    </div>
  );
};

interface ChatMessagesViewProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (inputValue: string, effort: string, model: string) => void;
  onCancel: () => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
}

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  liveActivityEvents,
  historicalActivities,
}: ChatMessagesViewProps) {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [isResearchExpanded, setIsResearchExpanded] = useState(true);

  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  return (
    <div className="flex flex-col h-full relative bg-neutral-800">
      {/* Main Content Area */}
      <ScrollArea className="flex-1 pb-24" ref={scrollAreaRef}>
        <div className="max-w-4xl mx-auto p-6 bg-neutral-800 min-h-full">
          {messages.map((message, index) => {
            const isLast = index === messages.length - 1;
            const isAI = message.type === "ai";
            const isHuman = message.type === "human";
            
            // Get activity events for this specific message
            const messageActivityEvents = isAI && message.id 
              ? historicalActivities[message.id] || []
              : [];
            
            // For the last AI message that's still loading, use live events
            const currentActivityEvents = isLast && isLoading && isAI
              ? liveActivityEvents
              : messageActivityEvents;

            return (
              <div key={message.id || `msg-${index}`} className="mb-8">
                {/* Human Message */}
                {isHuman && (
                  <div className="flex justify-end mb-4">
                    <HumanMessageBubble
                      message={message}
                      mdComponents={mdComponents}
                    />
                  </div>
                )}

                {/* Research Section - Between Human Query and AI Answer */}
                {isAI && (currentActivityEvents.length > 0 || (isLast && isLoading)) && (
                  <div className="mb-6 flex justify-start">
                    <div className="w-96 bg-neutral-800/30 backdrop-blur-sm rounded-lg border border-neutral-600/50 overflow-hidden">
                      <div 
                        className="p-3 border-b border-neutral-600/50 flex items-center gap-2 cursor-pointer hover:bg-neutral-700/30 transition-colors"
                        onClick={() => setIsResearchExpanded(!isResearchExpanded)}
                      >
                        {isResearchExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        <h3 className="text-sm font-semibold text-neutral-100">Research</h3>
                      </div>
                      {isResearchExpanded && (
                        currentActivityEvents.length > 0 ? (
                          <SimpleTimeline events={currentActivityEvents} isLoading={isLast && isLoading} />
                        ) : (
                          <div className="p-4 text-neutral-400 text-xs">
                            Research in progress...
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

                {/* AI Message - Final Answer */}
                {isAI && (
                  <div className="flex-1">
                    <div className="bg-neutral-800 text-neutral-100">
                      <ReactMarkdown components={mdComponents}>
                        {typeof message.content === "string"
                          ? message.content
                          : JSON.stringify(message.content)}
                      </ReactMarkdown>
                      <Button
                        variant="default"
                        className="cursor-pointer bg-neutral-700 border-neutral-600 text-neutral-300 mt-3"
                        onClick={() =>
                          handleCopy(
                            typeof message.content === "string"
                              ? message.content
                              : JSON.stringify(message.content),
                            message.id!
                          )
                        }
                      >
                        {copiedMessageId === message.id ? "Copied" : "Copy"}
                        {copiedMessageId === message.id ? <CopyCheck /> : <Copy />}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading State for New Query */}
          {isLoading &&
            (messages.length === 0 ||
              messages[messages.length - 1].type === "human") && (
              <div>
                {/* Research Section for Loading */}
                <div className="mb-6 flex justify-start">
                  <div className="w-96 bg-neutral-800/30 backdrop-blur-sm rounded-lg border border-neutral-600/50 overflow-hidden">
                    <div 
                      className="p-3 border-b border-neutral-600/50 flex items-center gap-2 cursor-pointer hover:bg-neutral-700/30 transition-colors"
                      onClick={() => setIsResearchExpanded(!isResearchExpanded)}
                    >
                      {isResearchExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      <h3 className="text-sm font-semibold text-neutral-100">Research</h3>
                    </div>
                    {isResearchExpanded && (
                      liveActivityEvents.length > 0 ? (
                        <SimpleTimeline events={liveActivityEvents} isLoading={true} />
                      ) : (
                        <div className="p-4 text-neutral-400 text-xs">
                          Starting research...
                        </div>
                      )
                    )}
                  </div>
                </div>

                {/* Loading Answer */}
                <div className="flex items-start gap-3">
                  <div className="flex-1 bg-neutral-800 text-neutral-100 rounded-xl p-4 min-h-[56px]">
                    <div className="flex items-center justify-start h-full">
                      <Loader2 className="h-5 w-5 animate-spin text-neutral-400 mr-2" />
                      <span>Generating answer...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
        </div>
      </ScrollArea>

      {/* Fixed Input Form at Bottom Center */}
      <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-neutral-800 via-neutral-800/95 to-transparent p-4 pt-8 pointer-events-none">
        <div className="max-w-2xl mx-auto pointer-events-auto">
          <InputForm
            onSubmit={onSubmit}
            isLoading={isLoading}
            onCancel={onCancel}
            hasHistory={messages.length > 0}
          />
        </div>
      </div>
    </div>
  );
}
