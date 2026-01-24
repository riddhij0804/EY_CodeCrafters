import { useState, useRef, useEffect } from 'react';
import { Send, Check, CheckCheck, Phone, Video, MoreVertical, Mic, MicOff, User, X, CreditCard } from 'lucide-react';
import { createRazorpayOrder, verifyRazorpayPayment } from '../services/paymentService';
import { getTierInfo } from '../services/loyaltyService';
import API_ENDPOINTS from '../config/api';
import sessionStore from '../lib/session';

const SESSION_API = API_ENDPOINTS.SESSION_MANAGER;
const SALES_API = API_ENDPOINTS.SALES_AGENT;

const Chat = () => {
  // Session state
  const [sessionInfo, setSessionInfo] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showPhoneInput, setShowPhoneInput] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [loyaltyPoints, setLoyaltyPoints] = useState(0);
  const [loyaltyTier, setLoyaltyTier] = useState('Bronze');
  const [userId, setUserId] = useState(null);

  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState(new Set());
  const [expandedCards, setExpandedCards] = useState(new Set());
  const [isRazorpayReady, setIsRazorpayReady] = useState(false);
  const [isPaymentProcessing, setIsPaymentProcessing] = useState(false);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const transcriptRef = useRef('');
  const paymentInFlightRef = useRef(false);

  // Helper to normalize surrounding quotes from messages so we only add one pair
  const normalizeQuotes = (text) => {
    if (!text) return '';
    return String(text).replace(/^\s*["'“”]+|["'“”]+\s*$/g, '').trim();
  };

  // Loyalty Management
  const fetchLoyaltyPoints = async (user_id) => {
    try {
      const result = await getTierInfo(user_id);
      if (result && result.points !== undefined) {
        setLoyaltyPoints(result.points);
        setLoyaltyTier(result.tier || 'Bronze');
      }
    } catch (error) {
      console.error('Failed to fetch loyalty info:', error);
      // Gracefully handle error - set defaults so UI doesn't break
      setLoyaltyPoints(0);
      setLoyaltyTier('Bronze');
    }
  };

  // Session Management Functions
  const startOrRestoreSession = async (phone) => {
    setIsLoadingSession(true);
    try {
      const storedPhone = sessionStore.getPhone();
      const storedToken = sessionStore.getSessionToken();

      if (storedPhone === phone && storedToken) {
        // Try to restore existing session for this phone
        try {
          const restoreResp = await fetch(`${SESSION_API}/session/restore`, {
            method: 'GET',
            headers: { 'X-Session-Token': storedToken }
          });

          if (restoreResp.ok) {
            const restoreData = await restoreResp.json();
            setSessionToken(storedToken);
            setSessionInfo(restoreData.session);
            setShowPhoneInput(false);
            sessionStore.setPhone(phone);

            // Extract user_id and fetch loyalty points
            const user_id = restoreData.session.data?.user_id || restoreData.session.user_id || '101';
            setUserId(user_id);
            await fetchLoyaltyPoints(user_id);

            if (restoreData.session.data?.chat_context?.length > 0) {
                      const chatMessages = restoreData.session.data.chat_context.map((msg, idx) => ({
                        id: idx + 1,
                        text: msg.message,
                        sender: msg.sender === 'user' ? 'user' : 'agent',
                        timestamp: new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                        status: 'read',
                        cards: msg.metadata?.cards || []
                      }));
              setMessages(chatMessages);
            }
            setIsLoadingSession(false);
            return;
          }
        } catch (err) {
          console.warn('Stored session restore failed, falling back to start', err);
        }
      }

      // Start new session for this phone
      const response = await fetch(`${SESSION_API}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: phone,
          channel: 'whatsapp'
        })
      });

      if (!response.ok) throw new Error('Failed to start session');

      const data = await response.json();
      setSessionToken(data.session_token);
      sessionStore.setSessionToken(data.session_token);
      sessionStore.setPhone(phone);
      setSessionInfo(data.session);
      setShowPhoneInput(false);

      // Extract user_id and fetch loyalty points
      const user_id = data.session.data?.user_id || data.session.user_id || '101';
      setUserId(user_id);
      await fetchLoyaltyPoints(user_id);

      // Load chat history from session
      if (data.session.data.chat_context && data.session.data.chat_context.length > 0) {
        const chatMessages = data.session.data.chat_context.map((msg, idx) => ({
          id: idx + 1,
          text: msg.message,
          sender: msg.sender === 'user' ? 'user' : 'agent',
          timestamp: new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          status: 'read'
        }));
        setMessages(chatMessages);
      } else {
        // Initial greeting
        setMessages([{
          id: 1,
          text: "Hello! I'm your AI Sales Agent. How can I help you today?",
          sender: 'agent',
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          status: 'read'
        }]);
      }
    } catch (error) {
      console.error('Session error:', error);
      alert('Failed to start session. Please try again.');
    } finally {
      setIsLoadingSession(false);
    }
  };

  const endSession = async () => {
    if (!sessionToken) return;

    try {
      await fetch(`${SESSION_API}/session/end`, {
        method: 'POST',
        headers: { 'X-Session-Token': sessionToken }
      });

      // Reset UI
      setSessionInfo(null);
      setSessionToken(null);
      sessionStore.clearAll();
      setMessages([]);
      setShowPhoneInput(true);
      setPhoneNumber('');
    } catch (error) {
      console.error('End session error:', error);
    }
  };

  const saveChatMessage = async (sender, message, metadata = null) => {
    if (!sessionToken) return;

    try {
      const payload = { sender, message };
      if (metadata) payload.metadata = metadata;

      await fetch(`${SESSION_API}/session/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': sessionToken
        },
        body: JSON.stringify({
          action: 'chat_message',
          payload
        })
      });
    } catch (error) {
      console.error('Failed to save chat message:', error);
    }
  };

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Initialize Speech Recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';

        for (let i = 0; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          }
        }

        if (finalTranscript) {
          transcriptRef.current += finalTranscript;
          setInputText(transcriptRef.current);
        }
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };
    }
  }, []);

  useEffect(() => {
    if (window.Razorpay) {
      setIsRazorpayReady(true);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => setIsRazorpayReady(true);
    script.onerror = () => {
      console.error('Failed to load Razorpay checkout script');
      setIsRazorpayReady(false);
    };

    document.body.appendChild(script);

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, []);

  // Mock agent responses
  const mockAgentResponses = [
    "Sure! Let me check the best options for you.",
    "I found some great products that match your preferences!",
    "Would you like me to show you our top recommendations?",
    "I can help you with that. What's your budget?",
    "Great choice! Let me find similar items for you.",
    "I'm checking our inventory for you...",
    "Based on your preferences, I have some perfect options!"
  ];

  const initiateRazorpayPayment = async (amount, product = null) => {
    if (!sessionToken) {
      alert('Start a chat session before initiating payment.');
      return;
    }

    if (!window.Razorpay || !isRazorpayReady) {
      alert('Razorpay checkout is still loading. Please wait a moment and try again.');
      return;
    }

    const parsedAmount = Number(amount);
    if (Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      alert('Please enter a valid amount in rupees.');
      return;
    }

    setIsPaymentProcessing(true);
    paymentInFlightRef.current = true;

    try {
      const orderResponse = await createRazorpayOrder({
        amount_rupees: parsedAmount,
        currency: 'INR',
        notes: {
          session_id: sessionInfo?.session_id || '',
          phone: sessionInfo?.phone || '',
        },
      });

      const options = {
        key: orderResponse.razorpay_key_id,
        amount: orderResponse.order.amount,
        currency: orderResponse.order.currency,
        name: 'EY CodeCrafters',
        description: 'AI Sales Agent Order',
        order_id: orderResponse.order.id,
        prefill: {
          name: sessionInfo?.data?.customer_name || sessionInfo?.phone || 'Customer',
          email: sessionInfo?.data?.email || 'test@example.com',
          contact: sessionInfo?.phone || '',
        },
        theme: { color: '#008069' },
        modal: {
          ondismiss: async () => {
            if (paymentInFlightRef.current) {
              const infoText = 'ℹ️ Razorpay checkout was closed before completing the payment.';
              const infoMessage = {
                id: Date.now() + Math.random(),
                text: infoText,
                sender: 'agent',
                timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                status: 'read',
              };
              setMessages((prev) => [...prev, infoMessage]);
              await saveChatMessage('agent', infoText);
            }
            paymentInFlightRef.current = false;
            setIsPaymentProcessing(false);
          },
        },
        handler: async (response) => {
          try {
            await verifyRazorpayPayment({
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_signature: response.razorpay_signature,
              amount_rupees: parsedAmount,
              user_id: sessionInfo?.data?.customer_id || sessionInfo?.phone,
              method: 'razorpay',
            });

            // Refresh loyalty points after payment
            await fetchLoyaltyPoints(userId);

            let successText = `✅ Payment of ₹${parsedAmount} received!\nPayment ID: ${response.razorpay_payment_id}`;
            
            // Add product-specific message and rewards
            if (product) {
              successText += `\n\n🎉 Purchase Complete!\n📦 ${product.name}\n💰 Amount Paid: ₹${parsedAmount}`;
              
              // Show rewards earned (this will be updated by the payment service)
              successText += `\n\n🎁 Rewards Earned:\n💎 Loyalty points added to your account!\n🏅 Check your updated tier status above.`;
            }

            const successMessage = {
              id: Date.now() + Math.random(),
              text: successText,
              sender: 'agent',
              timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
              status: 'read',
            };
            setMessages((prev) => [...prev, successMessage]);
            await saveChatMessage('agent', successText);
          } catch (verifyError) {
            console.error('Payment verification failed:', verifyError);
            const failureText = `⚠️ Payment captured but verification failed. Please contact support. (${verifyError.message || 'Unknown error'})`;
            const failMessage = {
              id: Date.now() + Math.random(),
              text: failureText,
              sender: 'agent',
              timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
              status: 'read',
            };
            setMessages((prev) => [...prev, failMessage]);
            await saveChatMessage('agent', failureText);
          } finally {
            paymentInFlightRef.current = false;
            setIsPaymentProcessing(false);
          }
        },
      };

      const razorpayInstance = new window.Razorpay(options);
      razorpayInstance.on('payment.failed', async (failure) => {
        console.error('Razorpay payment failed:', failure);
        const failureText = `❌ Payment failed: ${failure.error?.description || 'Unknown error'}`;
        const failMessage = {
          id: Date.now() + Math.random(),
          text: failureText,
          sender: 'agent',
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          status: 'read',
        };
        setMessages((prev) => [...prev, failMessage]);
        await saveChatMessage('agent', failureText);
        paymentInFlightRef.current = false;
        setIsPaymentProcessing(false);
      });

      razorpayInstance.open();
    } catch (error) {
      console.error('Failed to initiate Razorpay payment:', error);
      const errorText = `❌ Unable to start Razorpay checkout: ${error.message || 'Unknown error'}`;
      const failMessage = {
        id: Date.now() + Math.random(),
        text: errorText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
      };
      setMessages((prev) => [...prev, failMessage]);
      await saveChatMessage('agent', errorText);
      paymentInFlightRef.current = false;
      setIsPaymentProcessing(false);
    }
  };

  const handleProductPurchase = async (product) => {
    if (!sessionToken || !userId) {
      alert('Please start a chat session first.');
      return;
    }

    if (isPaymentProcessing) {
      return;
    }

    setIsPaymentProcessing(true);

    try {
      // Step 1: Calculate discounts
      const discountResponse = await fetch(`${API_ENDPOINTS.LOYALTY}/loyalty/calculate-discounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          cart_total: parseFloat(product.price)
        })
      });

      if (!discountResponse.ok) {
        throw new Error('Failed to calculate discounts');
      }

      const discountData = await discountResponse.json();

      // Step 2: Show discount breakdown to user
      const originalPrice = discountData.original_total;
      const finalPrice = discountData.final_total;
      const savings = originalPrice - finalPrice;

      const discountMessage = `🛒 **Purchase Summary**\n\n` +
        `📦 Product: ${product.name}\n` +
        `💰 Original Price: ₹${originalPrice}\n` +
        `${discountData.message}\n` +
        `💸 You Save: ₹${savings.toFixed(2)}\n` +
        `✅ Final Price: ₹${finalPrice.toFixed(2)}\n\n` +
        `🎁 Your Loyalty Status:\n` +
        `🏅 Tier: ${loyaltyTier}\n` +
        `💎 Points: ${loyaltyPoints}\n\n` +
        `Ready to proceed with payment?`;

      // Add discount summary message
      const discountMsg = {
        id: Date.now(),
        text: discountMessage,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, discountMsg]);
      await saveChatMessage('agent', discountMessage);

      // Step 3: Process payment
      await initiateRazorpayPayment(finalPrice.toFixed(2), product);

    } catch (error) {
      console.error('Purchase error:', error);
      alert('Failed to process purchase. Please try again.');
    } finally {
      setIsPaymentProcessing(false);
    }
  };

  const handlePaymentClick = async () => {
    // You can implement a generic payment action here if needed.
    // For now, it does nothing.
  };

  const handleSendMessage = async () => {
    if (!inputText.trim() || !sessionToken) return;

    const messageText = inputText;
    setInputText('');

    // Add user message
    const userMessage = {
      id: Date.now(),
      text: messageText,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      status: 'sent'
    };

    setMessages(prev => [...prev, userMessage]);

    // Save to backend
    await saveChatMessage('user', messageText);

    // Simulate message status updates (sent → delivered → read)
    setTimeout(() => {
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id ? { ...msg, status: 'delivered' } : msg
      ));
    }, 500);

    setTimeout(() => {
      setMessages(prev => prev.map(msg => 
        msg.id === userMessage.id ? { ...msg, status: 'read' } : msg
      ));
    }, 1000);

    // Show typing indicator
    setIsTyping(true);

    // Call Sales Agent API
    try {
      const payload = {
        message: messageText,
        session_token: sessionToken,
        metadata: { user_id: sessionInfo?.data?.customer_id || sessionInfo?.phone }
      };

      const resp = await fetch(`${SALES_API}/api/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      setIsTyping(false);

      if (!resp.ok) throw new Error('Agent error');

      const data = await resp.json();
      const agentText = data.reply || 'Sorry, I could not process that.';

      // Update session token if returned
      if (data.session_token) setSessionToken(data.session_token);

      const agentMessage = {
        id: Date.now() + 1,
        text: agentText,
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read',
        cards: data.cards || []  // Add product cards from API response
      };

      setMessages(prev => [...prev, agentMessage]);
      await saveChatMessage('agent', agentText, { cards: agentMessage.cards || [] });
    } catch (error) {
      setIsTyping(false);
      console.error('Agent call failed:', error);
      const failMsg = {
        id: Date.now() + 2,
        text: 'Sorry, I could not reach the agent. Please try again later.',
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        status: 'read'
      };
      setMessages(prev => [...prev, failMsg]);
      await saveChatMessage('agent', failMsg.text);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const toggleVoiceRecording = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser. Please use Chrome or Edge.');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      transcriptRef.current = '';
      setInputText('');
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const getMessageStatusIcon = (status) => {
    switch(status) {
      case 'sent':
        return <Check className="w-4 h-4 text-gray-400" />;
      case 'delivered':
        return <CheckCheck className="w-4 h-4 text-gray-400" />;
      case 'read':
        return <CheckCheck className="w-4 h-4 text-blue-500" />;
      default:
        return null;
    }
  };

  const toggleExpandMessage = (id) => {
    setExpandedMessages(prev => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  const toggleExpandCard = (id) => {
    setExpandedCards(prev => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  // Phone Input Modal
  if (showPhoneInput) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#efeae2]">
        <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full mx-4">
          <div className="text-center mb-6">
            <div className="w-20 h-20 bg-[#25d366] rounded-full flex items-center justify-center mx-auto mb-4">
              <Phone className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-[#008069] mb-2">WhatsApp Chat</h2>
            <p className="text-gray-600">Enter your phone number to start or continue your session</p>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-[#25d366] focus:outline-none text-lg"
                onKeyPress={(e) => e.key === 'Enter' && !isLoadingSession && phoneNumber.trim() && startOrRestoreSession(phoneNumber)}
              />
            </div>
            
            <button
              onClick={() => startOrRestoreSession(phoneNumber)}
              disabled={isLoadingSession || !phoneNumber.trim()}
              className="w-full bg-[#25d366] text-white py-3 rounded-lg font-semibold hover:bg-[#20bd5a] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {isLoadingSession ? 'Connecting...' : 'Start Chat'}
            </button>
            
            <p className="text-xs text-gray-500 text-center">
              Your session stays active and is reusable across WhatsApp and Kiosk.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0 bg-[#efeae2]">
      {/* Header - WhatsApp style */}
      <div className="bg-[#008069] text-white px-4 py-3 flex items-center justify-between shadow-md">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-[#d9d9d9] flex items-center justify-center text-[#128c7e] font-semibold text-lg">
              AI
            </div>
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-[#25d366] rounded-full border-2 border-[#008069]"></div>
          </div>
          <div>
            <h1 className="font-semibold text-base">AI Sales Agent</h1>
            <p className="text-xs text-[#d9d9d9]">online</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Loyalty Points & Tier Badge */}
          {loyaltyPoints > 0 && (
            <div className="flex items-center gap-2 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 px-3 py-1.5 rounded-full border border-yellow-500/50">
              <span className="text-xl">
                {loyaltyTier === 'Platinum' ? '💎' : loyaltyTier === 'Gold' ? '🥇' : loyaltyTier === 'Silver' ? '🥈' : '🥉'}
              </span>
              <div className="text-sm">
                <div className="flex items-center gap-1">
                  <span className="font-bold text-white">{loyaltyPoints}</span>
                  <span className="text-xs text-yellow-200">pts</span>
                </div>
                <div className="text-[10px] text-yellow-300 -mt-0.5 font-semibold">{loyaltyTier}</div>
              </div>
            </div>
          )}
          <button className="hover:bg-[#017561] p-2 rounded-full transition-colors">
            <Video className="w-5 h-5" />
          </button>
          <button className="hover:bg-[#017561] p-2 rounded-full transition-colors">
            <Phone className="w-5 h-5" />
          </button>
          <button 
            onClick={endSession}
            className="hover:bg-[#c0392b] p-2 rounded-full transition-colors"
            title="End Session"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Session Continuity Banner */}
      {sessionInfo && (
        <div className="bg-gradient-to-r from-[#dcf8c6] to-[#d0f4de] border-b-2 border-[#25d366] px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-[#25d366] rounded-full animate-pulse"></div>
              <div className="text-sm">
                <span className="font-semibold text-[#075e54]">Session Active:</span>
                <span className="ml-2 text-[#128c7e] font-mono text-xs">{sessionInfo.session_id}</span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs text-[#075e54]">
              <div className="flex items-center gap-1">
                <User className="w-3 h-3" />
                <span className="font-medium">{sessionInfo.phone}</span>
              </div>
              <div className="px-2 py-1 bg-white/50 rounded-full">
                <span className="font-semibold">📱 WhatsApp</span>
              </div>
              {sessionInfo.data?.chat_context?.length > 1 && (
                <div className="text-[#00796b] font-medium">
                  ↻ Session restored ({sessionInfo.data.chat_context.length} messages)
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chat Messages Area */}
      <div 
        className="flex-1 overflow-y-auto px-4 py-6 space-y-3 min-h-0"
        style={{
          backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'100\' height=\'100\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23d9d9d9\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M0 0h50v50H0zM50 50h50v50H50z\'/%3E%3C/g%3E%3C/svg%3E")',
        }}
      >
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] md:max-w-[65%] rounded-lg px-4 py-2 shadow-sm ${
                message.sender === 'user'
                  ? 'bg-[#d9fdd3] text-gray-900'
                  : 'bg-white text-gray-900'
              }`}
            >
              <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                {message.text && message.text.length > 800 && !expandedMessages.has(message.id)
                  ? `${message.text.slice(0, 380)}... `
                  : message.text}
                {message.text && message.text.length > 800 && (
                  <button
                    onClick={() => toggleExpandMessage(message.id)}
                    className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                  >
                    {expandedMessages.has(message.id) ? 'Show less' : 'Show more'}
                  </button>
                )}
              </div>
              
              {/* Product Cards */}
              {message.cards && message.cards.length > 0 && (
                <div className="mt-3 space-y-2">
                  {message.cards.map((card, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:bg-gray-100 transition-colors">
                      <div className="flex gap-3">
                        {card.image && (
                          <img 
                            src={card.image} 
                            alt={card.name} 
                            className="w-16 h-16 object-cover rounded"
                            onError={(e) => e.target.style.display = 'none'}
                          />
                        )}
                        <div className="flex-1">
                          <h4 className="font-semibold text-sm text-gray-900">{card.name}</h4>
                          <p className="text-xs text-gray-600 mt-1">{card.sku}</p>
                          {card.price && (
                            <p className="text-sm font-bold text-green-600 mt-1">₹{card.price}</p>
                          )}
                          {/* Show personalized reason AND gift message (if present). Fall back to description only if neither exists. */}
                          {(card.personalized_reason || card.gift_message || card.description) && (
                            <div className="mt-2 text-xs text-gray-500">
                              {/* Personalized reason (primary) */}
                              {card.personalized_reason && (
                                <div className="mb-2">
                                  {card.personalized_reason.length > 240 && !expandedCards.has(`${message.id}-${idx}-pr`)
                                    ? `${card.personalized_reason.slice(0, 220)}... `
                                    : card.personalized_reason}
                                  {card.personalized_reason.length > 240 && (
                                    <button
                                      onClick={() => toggleExpandCard(`${message.id}-${idx}-pr`)}
                                      className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                                    >
                                      {expandedCards.has(`${message.id}-${idx}-pr`) ? 'Show less' : 'Show more'}
                                    </button>
                                  )}
                                </div>
                              )}

                              {/* Gift message heading + message (italic, green, same size as description) */}
                              {card.gift_message && (
                                <div className="mb-2">
                                  <div className="text-xs font-medium text-[#075e54] mb-1">Gift message to attach:</div>
                                  <div className="italic text-xs text-[#0b6655]">
                                    {(() => {
                                      const gm = normalizeQuotes(card.gift_message);
                                      if (!gm) return null;
                                      const short = gm.length > 240 && !expandedCards.has(`${message.id}-${idx}-gift`);
                                      return (
                                        <>
                                          {short ? `"${gm.slice(0,220)}..." ` : `"${gm}"`}
                                          {gm.length > 240 && (
                                            <button
                                              onClick={() => toggleExpandCard(`${message.id}-${idx}-gift`)}
                                              className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                                            >
                                              {expandedCards.has(`${message.id}-${idx}-gift`) ? 'Show less' : 'Show more'}
                                            </button>
                                          )}
                                        </>
                                      );
                                    })()}
                                  </div>
                                </div>
                              )}

                              {/* If neither personalized nor gift message exist, show description with expand */}
                              {(!card.personalized_reason && !card.gift_message && card.description) && (
                                <>
                                  {card.description.length > 240 && !expandedCards.has(`${message.id}-${idx}`)
                                    ? `${card.description.slice(0, 220)}... `
                                    : card.description}
                                  {card.description.length > 240 && (
                                    <button
                                      onClick={() => toggleExpandCard(`${message.id}-${idx}`)}
                                      className="ml-1 text-xs text-[#00796b] font-medium hover:underline"
                                    >
                                      {expandedCards.has(`${message.id}-${idx}`) ? 'Show less' : 'Show more'}
                                    </button>
                                  )}
                                </>
                              )}

                              {/* Gift suitability tag */}
                              {card.gift_suitability && (
                                <div className="mt-1 inline-block bg-yellow-50 text-yellow-800 px-2 py-0.5 rounded-full text-[11px] font-medium">
                                  🎁 {card.gift_suitability}
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Purchase Button */}
                          <div className="mt-3 flex justify-end">
                            <button
                              onClick={() => handleProductPurchase(card)}
                              disabled={isPaymentProcessing}
                              className="bg-[#00796b] hover:bg-[#00695c] disabled:bg-gray-400 text-white text-xs font-medium px-3 py-1.5 rounded-md transition-colors flex items-center gap-1"
                            >
                              <CreditCard className="w-3 h-3" />
                              {isPaymentProcessing ? 'Processing...' : 'Buy Now'}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <div className={`flex items-center gap-1 justify-end mt-1 ${
                message.sender === 'user' ? 'text-gray-600' : 'text-gray-500'
              }`}>
                <span className="text-[10px]">{message.timestamp}</span>
                {message.sender === 'user' && getMessageStatusIcon(message.status)}
              </div>
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white rounded-lg px-4 py-3 shadow-sm">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area - WhatsApp style */}
      <div className="bg-[#f0f2f5] px-4 py-3 border-t border-gray-200">
        <div className="flex items-end gap-2">
          <div className="flex-1 bg-white rounded-full px-4 py-2 flex items-center gap-2 shadow-sm">
            <button className="text-gray-500 hover:text-gray-700">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9.153 11.603c.795 0 1.439-.879 1.439-1.962s-.644-1.962-1.439-1.962-1.439.879-1.439 1.962.644 1.962 1.439 1.962zm-3.204 1.362c-.026-.307-.131 5.218 6.063 5.551 6.066-.25 6.066-5.551 6.066-5.551-6.078 1.416-12.129 0-12.129 0zm11.363 1.108s-.669 1.959-5.051 1.959c-3.505 0-5.388-1.164-5.607-1.959 0 0 5.912 1.055 10.658 0zM11.804 1.011C5.609 1.011.978 6.033.978 12.228s4.826 10.761 11.021 10.761S23.02 18.423 23.02 12.228c.001-6.195-5.021-11.217-11.216-11.217zM12 21.354c-5.273 0-9.381-3.886-9.381-9.159s3.942-9.548 9.215-9.548 9.548 4.275 9.548 9.548c-.001 5.272-4.109 9.159-9.382 9.159zm3.108-9.751c.795 0 1.439-.879 1.439-1.962s-.644-1.962-1.439-1.962-1.439.879-1.439 1.962.644 1.962 1.439 1.962z"/>
              </svg>
            </button>
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message"
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-gray-500"
            />
            <button
              onClick={handlePaymentClick}
              disabled={!sessionToken || !isRazorpayReady || isPaymentProcessing}
              className={`transition-colors ${(!sessionToken || !isRazorpayReady || isPaymentProcessing) ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:text-gray-700'}`}
              title={isPaymentProcessing ? 'Processing payment...' : 'Collect payment via Razorpay'}
            >
              <CreditCard className="w-6 h-6" />
            </button>
            <button 
              onClick={toggleVoiceRecording}
              className={`transition-colors ${
                isRecording 
                  ? 'text-red-500 hover:text-red-700 animate-pulse' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              title={isRecording ? 'Stop recording' : 'Start voice input'}
            >
              {isRecording ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
            </button>
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputText.trim()}
            className={`rounded-full p-3 transition-all ${
              inputText.trim()
                ? 'bg-[#008069] hover:bg-[#017561] text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
