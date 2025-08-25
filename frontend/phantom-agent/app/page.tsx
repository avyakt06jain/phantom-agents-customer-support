"use client";

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { Toaster } from '@/components/ui/toaster';
import { Send, Upload, FileText, Bot, User } from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
  documentHash?: string;
  isStreaming?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'ai',
      content: "Hello! I'm your AI customer support assistant. I'm here to help you 24/7. You can ask me questions or upload documents for analysis.",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileUpload = (file: File) => {
    const allowedTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload PDF, TXT, or DOCX files only.",
        variant: "destructive",
      });
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      toast({
        title: "File too large",
        description: "Please upload files smaller than 10MB.",
        variant: "destructive",
      });
      return;
    }

    setUploadedFile(file);
    toast({
      title: "File uploaded",
      description: `${file.name} is ready for analysis.`,
    });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const simulateStreaming = async (response: string, messageId: string, documentHash?: string) => {
    const words = response.split(' ');
    let currentContent = '';
    
    for (let i = 0; i < words.length; i++) {
      currentContent += (i > 0 ? ' ' : '') + words[i];
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, content: currentContent, documentHash, isStreaming: i < words.length - 1 }
          : msg
      ));
      
      // Simulate typing delay
      await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100));
    }
  };

//   const sendMessage = async () => {
//     if (!input.trim() && !uploadedFile) return;

//     const userMessage: Message = {
//       id: Date.now().toString(),
//       type: 'user',
//       content: input || `Uploaded: ${uploadedFile?.name}`,
//       timestamp: new Date(),
//     };

//     setMessages(prev => [...prev, userMessage]);
//     setInput('');
//     setIsLoading(true);

//     // Create placeholder AI message for streaming
//     const aiMessageId = (Date.now() + 1).toString();
//     const aiMessage: Message = {
//       id: aiMessageId,
//       type: 'ai',
//       content: '',
//       timestamp: new Date(),
//       isStreaming: true,
//     };

//     setMessages(prev => [...prev, aiMessage]);

//     try {
//       const formData = new FormData();
//       formData.append('question', input);
//       if (uploadedFile) {
//         formData.append('document', uploadedFile);
//       }

//       const response = await fetch('https://avyakt06jain-phantom-agents-customer-support.hf.space/process', {
//         method: 'POST',
//         body: formData,
//       });

//       if (!response.ok) {
//         throw new Error('Failed to get response');
//       }

//       const data = await response.json();
      
//       // Start streaming simulation
//       await simulateStreaming(data.answer, aiMessageId, data.document_hash);
      
//       // Clear uploaded file after successful processing
//       setUploadedFile(null);
      
//     } catch (error) {
//       console.error('Error:', error);
//       setMessages(prev => prev.map(msg => 
//         msg.id === aiMessageId 
//           ? { ...msg, content: "I'm sorry, I'm having trouble processing your request right now. Please try again later.", isStreaming: false }
//           : msg
//       ));
      
//       toast({
//         title: "Error",
//         description: "Failed to get AI response. Please try again.",
//         variant: "destructive",
//       });
//     } finally {
//       setIsLoading(false);
//     }
//   };


const sendMessage = async () => {
  if (!input.trim() && !uploadedFile) return;

  const userMessage: Message = {
    id: Date.now().toString(),
    type: 'user',
    content: input || `Uploaded: ${uploadedFile?.name}`,
    timestamp: new Date(),
  };

  setMessages(prev => [...prev, userMessage]);
  setInput('');
  setIsLoading(true);

  // Create placeholder AI message for streaming
  const aiMessageId = (Date.now() + 1).toString();
  const aiMessage: Message = {
    id: aiMessageId,
    type: 'ai',
    content: '',
    timestamp: new Date(),
    isStreaming: true,
  };
  setMessages(prev => [...prev, aiMessage]);

  try {
    // Prepare form data
    const formData = new FormData();
    formData.append('query', input);

    // Add conversation history
    const history = messages.map(m => ({
      role: m.type === 'user' ? 'user' : 'assistant',
      content: m.content,
    }));
    formData.append('history', JSON.stringify(history));

    // Add uploaded file if present
    if (uploadedFile) {
      formData.append('document', uploadedFile);
    }

    const API_KEY = "06864514c746f45fb93a6e0421a052c7875d3d1fd841d870f397c9d50e4146f8" 

    const response = await fetch('https://avyakt06jain-phantom-agents-customer-support.hf.space/process', {
      method: 'POST',
      body: formData,
      headers: {
         "Accept": "application/json",
        "Authorization": `Bearer ${API_KEY}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to get response');
    }

    const data = await response.json();

    // Start streaming simulation
    await simulateStreaming(data.answer, aiMessageId, data.document_hash);

    // Clear uploaded file after successful processing
    setUploadedFile(null);

  } catch (error) {
    console.error('Error:', error);
    setMessages(prev => prev.map(msg =>
      msg.id === aiMessageId
        ? { ...msg, content: "I'm sorry, I'm having trouble processing your request right now. Please try again later.", isStreaming: false }
        : msg
    ));

    toast({
      title: "Error",
      description: "Failed to get AI response. Please try again.",
      variant: "destructive",
    });
  } finally {
    setIsLoading(false);
  }
};


  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-4xl mx-auto h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white rounded-t-xl shadow-sm border-b p-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI Customer Support</h1>
              <p className="text-sm text-gray-600">24/7 Intelligent Assistant for SMEs</p>
            </div>
            <div className="ml-auto">
              <div className="flex items-center gap-2 text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">Online</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 bg-white">
          <ScrollArea ref={scrollAreaRef} className="h-full p-6">
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={message.id}
                  className={`flex gap-3 animate-in slide-in-from-bottom-2 duration-300 ${
                    message.type === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                  style={{
                    animationDelay: `${index * 100}ms`,
                  }}
                >
                  {message.type === 'ai' && (
                    <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                  )}
                  
                  <div className={`max-w-[70%] ${message.type === 'user' ? 'order-1' : ''}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 shadow-sm ${
                        message.type === 'user'
                          ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white ml-auto'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <p className="text-sm leading-relaxed">
                        {message.content}
                        {message.isStreaming && (
                          <span className="inline-block w-2 h-4 bg-current opacity-75 animate-pulse ml-1" />
                        )}
                      </p>
                    </div>
                    
                    {message.documentHash && (
                      <p className="text-xs text-gray-500 italic mt-1 px-2">
                        Document: {message.documentHash}
                      </p>
                    )}
                    
                    <p className="text-xs text-gray-500 mt-1 px-2">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>

                  {message.type === 'user' && (
                    <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>

        {/* File Upload Area */}
        {uploadedFile && (
          <div className="bg-white border-t p-4">
            <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <FileText className="w-5 h-5 text-blue-600" />
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900">{uploadedFile.name}</p>
                <p className="text-xs text-blue-600">
                  {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setUploadedFile(null)}
                className="text-blue-600 hover:text-blue-700"
              >
                Remove
              </Button>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="bg-white rounded-b-xl shadow-sm border-t p-6">
          <div
            className={`border-2 border-dashed rounded-xl p-4 mb-4 transition-colors ${
              isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <div className="flex items-center justify-center gap-2 text-gray-500">
              <Upload className="w-5 h-5" />
              <span className="text-sm">
                Drop files here or{' '}
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  browse
                </button>
              </span>
            </div>
            <p className="text-xs text-gray-400 text-center mt-1">
              Supports PDF, TXT, DOCX (max 10MB)
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.docx"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              className="hidden"
            />
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything or upload a document..."
                disabled={isLoading}
                className="h-12 text-base"
              />
            </div>
            <Button
              onClick={sendMessage}
              disabled={isLoading || (!input.trim() && !uploadedFile)}
              size="lg"
              className="h-12 px-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>
      </div>
      <Toaster />
    </div>
  );
}