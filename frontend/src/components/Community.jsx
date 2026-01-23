import React, { useState, useEffect, useRef } from 'react';
import { Send, Users, TrendingUp, MessageCircle, Phone, X, Sparkles, FileText } from 'lucide-react';

const SESSION_API = 'http://localhost:8000';
const VIRTUAL_CIRCLES_API = 'http://localhost:8009';

/**
 * Community Component - Virtual Circles Real Customer Chat
 * 
 * IMPORTANT: NO FAKE USERS
 * - All messages from REAL customers only (from customers.csv)
 * - AI never pretends to be a user
 * - AI only provides insights/summaries as "Style AI"
 * 
 * Flow: Frontend → Sales Agent → Virtual Circles Agent
 */
const Community = React.forwardRef((props, ref) => {
  // Session state (like Chat.jsx)
  const [sessionInfo, setSessionInfo] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showPhoneInput, setShowPhoneInput] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  
  // Circle state
  const [circles, setCircles] = useState([]);
  const [selectedCircle, setSelectedCircle] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [circleInfo, setCircleInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [userAlias, setUserAlias] = useState('');
  
  // AI Insights state
  const [aiRecommendation, setAiRecommendation] = useState(null);
  const [aiSummary, setAiSummary] = useState(null);
  const [showAiPanel, setShowAiPanel] = useState(false);
  
  const messagesEndRef = useRef(null);
  const userId = sessionInfo?.customer_id; // From session (mapped from phone)

  // Expose initialization method to parent
  React.useImperativeHandle(ref, () => ({
    initializeSession: () => {
      // If no session, show phone input automatically
      if (!sessionInfo && !showPhoneInput) {
        setShowPhoneInput(true);
      }
    }
  }));

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Start session (like Chat.jsx)
  const startOrRestoreSession = async (phone) => {
    setIsLoadingSession(true);
    try {
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
      console.log('Session response:', data);
      setSessionToken(data.session_token);
      setSessionInfo(data.session);
      
      const customerId = data.session.customer_id;
      console.log(`Customer ID from session: ${customerId}`);
      
      if (!customerId) {
        alert(`Phone number ${phone} not found in customer database. Please use a valid phone from customers.csv`);
        return;
      }
      
      setShowPhoneInput(false);

      // Now assign user to circle
      await assignUserToCircle(customerId);
    } catch (error) {
      console.error('Session error:', error);
      alert('Failed to start session. Please try again.');
    } finally {
      setIsLoadingSession(false);
    }
  };

  const handlePhoneSubmit = async (e) => {
    e.preventDefault();
    if (!phoneNumber.trim()) {
      alert('Please enter your phone number');
      return;
    }
    await startOrRestoreSession(phoneNumber);
  };

  // Assign user to a circle
  const assignUserToCircle = async (customerId) => {
    if (!customerId) {
      alert('Invalid phone number. Please use a phone number from customers.csv (e.g., 9000000002)');
      return;
    }
    
    try {
      setLoading(true);
      console.log(`Assigning customer ${customerId} to circle...`);
      const response = await fetch(
        `${VIRTUAL_CIRCLES_API}/circles/assign-user?user_id=${customerId}`,
        { method: 'POST' }
      );
      
      if (!response.ok) throw new Error('Failed to assign circle');
      
      const data = await response.json();
      setSelectedCircle(data.circle_id);
      
      // Load circle info and messages
      await loadCircleInfo(data.circle_id);
      await loadMessages(data.circle_id, customerId);
    } catch (error) {
      console.error('Error assigning circle:', error);
      alert('Failed to connect to community. Make sure Virtual Circles service is running on port 8009.');
    } finally {
      setLoading(false);
    }
  };

  // Load circle information
  const loadCircleInfo = async (circleId) => {
    try {
      const response = await fetch(`${VIRTUAL_CIRCLES_API}/circles/${circleId}`);
      if (!response.ok) throw new Error('Failed to load circle info');
      
      const data = await response.json();
      setCircleInfo(data);
    } catch (error) {
      console.error('Error loading circle info:', error);
    }
  };

  // Load chat messages
  const loadMessages = async (circleId, customerId) => {
    try {
      const response = await fetch(
        `${VIRTUAL_CIRCLES_API}/circle/${circleId}/chat/messages?user_id=${customerId}&limit=50`
      );
      
      if (!response.ok) throw new Error('Failed to load messages');
      
      const data = await response.json();
      setMessages(data.messages || []);
      setUserAlias(data.user_alias || 'You');
    } catch (error) {
      console.error('Error loading messages:', error);
    }
  };

  // Send message (REAL customer message only)
  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedCircle) return;

    const messageText = newMessage.trim();
    setNewMessage('');

    try {
      const response = await fetch(
        `${VIRTUAL_CIRCLES_API}/circle/${selectedCircle}/chat/send`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            text: messageText
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        alert(error.detail || 'Failed to send message');
        return;
      }

      const data = await response.json();
      
      // Add user message only (no automatic AI insights)
      setMessages(prev => [...prev, data.message]);
      
      scrollToBottom();
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Failed to send message. Please try again.');
    }
  };

  // Handle enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Refresh messages
  const refreshMessages = () => {
    if (selectedCircle) {
      loadMessages(selectedCircle, userId);
    }
  };

  // Get AI Recommendation
  const getAIRecommendation = async () => {
    if (!selectedCircle || !userId) return;
    
    try {
      setLoading(true);
      const response = await fetch(
        `${VIRTUAL_CIRCLES_API}/circle/${selectedCircle}/ai/recommend?user_id=${userId}`,
        { method: 'POST' }
      );
      
      if (!response.ok) throw new Error('Failed to get recommendation');
      
      const data = await response.json();
      setAiRecommendation(data);
      setShowAiPanel(true);
      
    } catch (error) {
      console.error('Error getting recommendation:', error);
      alert('Failed to get AI recommendation. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Get Chat Summary
  const getChatSummary = async () => {
    if (!selectedCircle || !userId) return;
    
    try {
      setLoading(true);
      const response = await fetch(
        `${VIRTUAL_CIRCLES_API}/circle/${selectedCircle}/ai/summarize?user_id=${userId}`,
        { method: 'POST' }
      );
      
      if (!response.ok) throw new Error('Failed to get summary');
      
      const data = await response.json();
      setAiSummary(data);
      setShowAiPanel(true);
      
    } catch (error) {
      console.error('Error getting summary:', error);
      alert('Failed to get chat summary. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Phone input screen
  if (showPhoneInput) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-purple-50">
        <div className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full mx-4">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mb-4">
              <Users className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Welcome to Community</h1>
            <p className="text-gray-600">Connect with shoppers like you</p>
          </div>

          <form onSubmit={handlePhoneSubmit} className="space-y-4">
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                <Phone className="inline w-4 h-4 mr-1" />
                Enter your phone number
              </label>
              <input
                id="phone"
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="9000000000"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoadingSession}
              />
            </div>

            <button
              type="submit"
              disabled={isLoadingSession || !phoneNumber.trim()}
              className={`w-full py-3 rounded-lg font-medium transition-colors ${
                isLoadingSession || !phoneNumber.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700'
              }`}
            >
              {isLoadingSession ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Connecting...
                </div>
              ) : (
                'Join Community'
              )}
            </button>
          </form>

          <p className="text-xs text-gray-500 text-center mt-4">
            By joining, you'll be matched with shoppers who share your style
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#efeae2]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#008069] mx-auto"></div>
          <p className="mt-4 text-[#075e54] font-medium">Finding your style community...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#efeae2]">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
      {/* Header - WhatsApp style */}
      <div className="bg-[#008069] text-white px-4 py-3 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-[#d9d9d9] flex items-center justify-center text-[#128c7e] font-semibold text-lg">
                SC
              </div>
              <div className="absolute bottom-0 right-0 w-3 h-3 bg-[#25d366] rounded-full border-2 border-[#008069]"></div>
            </div>
            <div>
              <h1 className="font-semibold text-base">Style Circle Community</h1>
              <p className="text-xs text-[#d9d9d9]">
                {sessionInfo ? 'Connected' : 'Join to connect with shoppers like you'}
              </p>
            </div>
          </div>
          
          {circleInfo && (
            <div className="flex items-center gap-4">
              <button
                onClick={refreshMessages}
                className="hover:bg-[#017561] p-2 rounded-full transition-colors"
                title="Refresh messages"
              >
                <MessageCircle className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Circle Info Banner - WhatsApp style */}
      {circleInfo && (
        <div className="bg-gradient-to-r from-[#dcf8c6] to-[#d0f4de] border-b-2 border-[#25d366] px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-[#075e54]" />
              <div className="text-sm">
                <span className="font-semibold text-[#075e54]">{circleInfo.circle_name || 'Style Circle'}</span>
                <span className="ml-2 text-[#128c7e]">• {circleInfo.user_count} members</span>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs text-[#075e54]">
              <div>
                <span className="font-medium">Trending:</span>
                <span className="ml-1">{circleInfo.top_brands?.slice(0, 2).join(', ') || 'Loading...'}</span>
              </div>
              <div className="px-2 py-1 bg-white/50 rounded-full">
                <span className="font-semibold">₹{Math.round(circleInfo.avg_order_value || 0)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages Area - WhatsApp style */}
      <div 
        className="flex-1 overflow-y-auto px-4 py-6 space-y-3"
        style={{
          backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'100\' height=\'100\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'%23d9d9d9\' fill-opacity=\'0.05\'%3E%3Cpath d=\'M0 0h50v50H0zM50 50h50v50H50z\'/%3E%3C/g%3E%3C/svg%3E")',
        }}
      >
        {/* AI Action Buttons */}
        <div className="flex items-center justify-center space-x-3 pb-4">
          <button
            onClick={getAIRecommendation}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-[#008069] text-white rounded-full hover:bg-[#017561] transition-all shadow-md disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span className="text-sm font-medium">Get AI Recommendation</span>
          </button>
          <button
            onClick={getChatSummary}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-[#075e54] text-white rounded-full hover:bg-[#064439] transition-all shadow-md disabled:opacity-50"
          >
            <FileText className="w-4 h-4" />
            <span className="text-sm font-medium">Summarize Chat</span>
          </button>
        </div>

        {messages.length === 0 ? (
          <div className="text-center py-12">
            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-[#075e54] mb-2">
              Welcome to Your Style Circle!
            </h3>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              Start a conversation with {circleInfo?.user_count || 0} shoppers who share your taste.
              <br />
              All messages are from REAL customers like you!
            </p>
            <p className="text-[#008069] text-sm mt-4 font-medium">
              👆 Try the AI buttons above for instant recommendations!
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.message_id}
              className={`flex ${msg.type === 'ai_insight' ? 'justify-center' : msg.alias === userAlias ? 'justify-end' : 'justify-start'}`}
            >
              {msg.type === 'ai_insight' ? (
                // AI Insight (NOT a user message)
                <div className="max-w-2xl w-full bg-[#fff4e5] border-l-4 border-[#ffa500] rounded-lg p-4 shadow-sm">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 w-8 h-8 bg-[#ffa500] rounded-full flex items-center justify-center">
                      <TrendingUp className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-semibold text-[#075e54] mb-1">
                        Style AI • Community Insight
                      </p>
                      <p className="text-sm text-gray-700">{msg.text}</p>
                      <p className="text-xs text-gray-400 mt-2">
                        {new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                // Real Customer Message - WhatsApp style
                <div
                  className={`max-w-[75%] md:max-w-[65%] rounded-lg px-4 py-2 shadow-sm ${
                    msg.alias === userAlias
                      ? 'bg-[#d9fdd3] text-gray-900'
                      : 'bg-white text-gray-900'
                  }`}
                >
                  <p className="text-xs font-semibold mb-1 ${
                    msg.alias === userAlias ? 'text-[#008069]' : 'text-[#075e54]'
                  }">
                    {msg.alias === userAlias ? 'You' : msg.alias}
                  </p>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">{msg.text}</p>
                  <div className="flex items-center gap-1 justify-end mt-1">
                    <span className="text-[10px] text-gray-600">
                      {new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area - WhatsApp style */}
      <div className="bg-[#f0f2f5] px-4 py-3 border-t border-gray-200">
        <div className="flex items-end gap-2">
          <div className="flex-1 bg-white rounded-full px-4 py-2 flex items-center gap-2 shadow-sm">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Share with your style circle..."
              className="flex-1 bg-transparent outline-none text-sm placeholder:text-gray-500"
              maxLength={500}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={!newMessage.trim()}
            className={`rounded-full p-3 transition-all ${
              newMessage.trim()
                ? 'bg-[#008069] hover:bg-[#017561] text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          ℹ️ All messages are from real customers • AI insights appear with orange badge
        </p>
      </div>
    </div>
    
    {/* AI Insights Sidebar Panel */}
    {showAiPanel && (aiRecommendation || aiSummary) && (
      <div className="w-96 bg-[#f0f2f5] border-l border-gray-300 flex flex-col overflow-hidden">
        {/* Panel Header - WhatsApp style */}
        <div className="bg-[#008069] px-4 py-3 flex items-center justify-between shadow-md">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-white" />
            <h2 className="text-white font-semibold">AI Insights</h2>
          </div>
          <button
            onClick={() => setShowAiPanel(false)}
            className="text-white hover:text-[#d9d9d9] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Panel Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* AI Recommendation Section */}
          {aiRecommendation && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-[#008069]" />
                <h3 className="font-semibold text-[#075e54]">Product Recommendation</h3>
              </div>
              
              <div className="bg-white rounded-lg p-4 border border-[#25d366] shadow-sm">
                <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                  {aiRecommendation.detailed_explanation || aiRecommendation.recommendation}
                </p>
              </div>
              
              {/* Product Cards */}
              {aiRecommendation.products && aiRecommendation.products.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-[#075e54]">Trending Products:</p>
                  {aiRecommendation.products.slice(0, 3).map((product, idx) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 hover:border-[#25d366] transition-colors shadow-sm">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-800">{product.brand}</p>
                          <p className="text-xs text-gray-600">{product.product}</p>
                          <div className="flex items-center space-x-3 mt-2">
                            <span className="text-xs bg-[#dcf8c6] text-[#075e54] px-2 py-1 rounded-full">
                              {product.users} peers
                            </span>
                            <span className="text-xs text-gray-500">{product.trend}</span>
                          </div>
                        </div>
                        <p className="text-sm font-bold text-[#008069]">₹{product.price}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              <p className="text-xs text-gray-500 flex items-center space-x-1">
                <Sparkles className="w-3 h-3" />
                <span>Powered by Vertex AI Gemini 2.5 Flash</span>
              </p>
            </div>
          )}
          
          {/* AI Summary Section */}
          {aiSummary && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <FileText className="w-5 h-5 text-[#008069]" />
                <h3 className="font-semibold text-[#075e54]">Chat Summary</h3>
              </div>
              
              <div className="bg-white rounded-lg p-4 border border-[#25d366] shadow-sm">
                <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                  {aiSummary.detailed_analysis || aiSummary.summary}
                </p>
              </div>
              
              {/* Stats Cards */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                  <p className="text-xs text-gray-500">Messages</p>
                  <p className="text-lg font-bold text-[#008069]">{aiSummary.message_count || 0}</p>
                </div>
                <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                  <p className="text-xs text-gray-500">Active Members</p>
                  <p className="text-lg font-bold text-[#008069]">{aiSummary.active_members || 0}</p>
                </div>
              </div>
              
              {/* Brands Mentioned */}
              {aiSummary.brands && aiSummary.brands.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-[#075e54]">Brands Discussed:</p>
                  <div className="flex flex-wrap gap-2">
                    {aiSummary.brands.map((brand, idx) => (
                      <span key={idx} className="text-xs bg-[#dcf8c6] text-[#075e54] px-3 py-1 rounded-full">
                        {brand}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <p className="text-xs text-gray-500 flex items-center space-x-1">
                <Sparkles className="w-3 h-3" />
                <span>Powered by Vertex AI Gemini 2.5 Flash</span>
              </p>
            </div>
          )}
        </div>
        
        {/* Panel Footer */}
        <div className="border-t border-gray-300 p-3 bg-white">
          <div className="flex space-x-2">
            <button
              onClick={getAIRecommendation}
              disabled={loading}
              className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-[#008069] text-white rounded-lg hover:bg-[#017561] transition-colors text-sm disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>Refresh Rec</span>
            </button>
            <button
              onClick={getChatSummary}
              disabled={loading}
              className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-[#075e54] text-white rounded-lg hover:bg-[#064439] transition-colors text-sm disabled:opacity-50"
            >
              <FileText className="w-4 h-4" />
              <span>Refresh Summary</span>
            </button>
          </div>
        </div>
      </div>
    )}
  </div>
  );
});

Community.displayName = 'Community';

export default Community;
