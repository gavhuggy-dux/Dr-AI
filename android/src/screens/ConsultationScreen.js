import React, { useEffect, useState, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  FlatList, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { colors, borderRadius } from '../theme';
import apiClient from '../api/client';
import AdTicker from '../components/AdTicker';
import AdCarousel from '../components/AdCarousel';

export default function ConsultationScreen({ route, navigation }) {
  const { appointmentId } = route.params || {};
  const [timeLeft, setTimeLeft] = useState(15 * 60); // 15 min in seconds
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isRunning, setIsRunning] = useState(true);
  const [sending, setSending] = useState(false);
  const flatListRef = useRef(null);

  useEffect(() => {
    if (appointmentId) {
      apiClient.startAppointment(appointmentId).catch(() => {});
    }
  }, [appointmentId]);

  // Timer countdown
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          setIsRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [isRunning]);

  // Welcome message
  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        text: 'Hello! I\'m Dr. AI. Please describe your symptoms or health concern, and I\'ll help you with a preliminary assessment.',
        sender: 'ai',
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  async function handleSend() {
    if (!inputText.trim() || sending) return;
    const userMessage = {
      id: Date.now().toString(),
      text: inputText.trim(),
      sender: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setSending(true);

    try {
      // Call the API for AI response
      const response = await apiClient.request('/api/consultation/message', {
        method: 'POST',
        body: JSON.stringify({
          appointment_id: appointmentId,
          message: userMessage.text,
        }),
      });

      const aiMessage = {
        id: (Date.now() + 1).toString(),
        text: response.reply || response.message || 'I understand your concern. Based on what you\'ve described, I recommend monitoring your symptoms and consulting with a healthcare provider if they persist. What other symptoms are you experiencing?',
        sender: 'ai',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (e) {
      // Fallback AI response
      const fallbackMessage = {
        id: (Date.now() + 1).toString(),
        text: 'Thank you for sharing that information. Based on common medical knowledge, I recommend staying hydrated and monitoring your symptoms. If symptoms persist for more than 48 hours, please consult a healthcare professional. Is there anything else you\'d like to ask?',
        sender: 'ai',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, fallbackMessage]);
    } finally {
      setSending(false);
    }
  }

  async function handleEndConsultation() {
    Alert.alert(
      'End Consultation',
      'Are you sure you want to end this consultation?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'End',
          style: 'destructive',
          onPress: async () => {
            setIsRunning(false);
            if (appointmentId) {
              try {
                await apiClient.completeAppointment(appointmentId);
              } catch (e) {
                console.error('Failed to complete:', e);
              }
            }
            navigation.goBack();
          },
        },
      ]
    );
  }

  function renderMessage({ item }) {
    const isUser = item.sender === 'user';
    return (
      <View style={[styles.messageRow, isUser ? styles.userRow : styles.aiRow]}>
        {!isUser && (
          <View style={styles.aiAvatar}>
            <Text style={styles.aiAvatarText}>AI</Text>
          </View>
        )}
        <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.aiBubble]}>
          <Text style={[styles.messageText, isUser ? styles.userText : styles.aiText]}>
            {item.text}
          </Text>
          <Text style={[styles.messageTime, isUser ? styles.userTime : styles.aiTime]}>
            {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </View>
      </View>
    );
  }

  const timerColor = timeLeft < 60 ? colors.error : timeLeft < 300 ? colors.warning : colors.accent;

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      {/* Top Ad Ticker */}
      <AdTicker />

      {/* Header with Timer */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleEndConsultation}>
          <Text style={styles.endBtn}>✕ End</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Dr. AI Consultation</Text>
        <View style={[styles.timerBadge, { borderColor: timerColor }]}>
          <Text style={[styles.timerText, { color: timerColor }]}>
            {formatTime(timeLeft)}
          </Text>
        </View>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => item.id}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
        ListFooterComponent={sending ? (
          <View style={styles.typingIndicator}>
            <Text style={styles.typingText}>Dr. AI is typing...</Text>
          </View>
        ) : null}
      />

      {/* Bottom Ad */}
      <AdCarousel height={60} />

      {/* Input Bar */}
      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={inputText}
          onChangeText={setInputText}
          placeholder={isRunning ? 'Type your message...' : 'Consultation ended'}
          placeholderTextColor={colors.textSecondary}
          editable={isRunning}
          multiline
          maxLength={500}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!inputText.trim() || !isRunning) && styles.sendBtnDisabled]}
          onPress={handleSend}
          disabled={!inputText.trim() || !isRunning || sending}
        >
          <Text style={styles.sendBtnText}>Send</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.card,
    borderBottomWidth: 1,
    borderBottomColor: colors.cardBorder,
  },
  endBtn: {
    fontSize: 14,
    color: colors.error,
    fontWeight: '600',
    padding: 4,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.white,
  },
  timerBadge: {
    borderWidth: 1.5,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  timerText: {
    fontSize: 16,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  messagesList: {
    padding: 16,
    paddingBottom: 8,
    flexGrow: 1,
  },
  messageRow: {
    flexDirection: 'row',
    marginBottom: 16,
    alignItems: 'flex-end',
  },
  userRow: {
    justifyContent: 'flex-end',
  },
  aiRow: {
    justifyContent: 'flex-start',
  },
  aiAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  aiAvatarText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.background,
  },
  messageBubble: {
    maxWidth: '78%',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userBubble: {
    backgroundColor: colors.accent,
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: colors.card,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  userText: {
    color: colors.background,
  },
  aiText: {
    color: colors.text,
  },
  messageTime: {
    fontSize: 11,
    marginTop: 4,
  },
  userTime: {
    color: colors.background + '80',
    textAlign: 'right',
  },
  aiTime: {
    color: colors.textSecondary,
  },
  typingIndicator: {
    paddingLeft: 40,
    paddingVertical: 4,
  },
  typingText: {
    fontSize: 13,
    color: colors.accent,
    fontStyle: 'italic',
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: colors.card,
    borderTopWidth: 1,
    borderTopColor: colors.cardBorder,
  },
  input: {
    flex: 1,
    backgroundColor: colors.inputBg,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    color: colors.white,
    maxHeight: 80,
    borderWidth: 1,
    borderColor: colors.inputBorder,
  },
  sendBtn: {
    backgroundColor: colors.accent,
    borderRadius: 20,
    paddingHorizontal: 18,
    paddingVertical: 10,
    marginLeft: 8,
  },
  sendBtnDisabled: {
    opacity: 0.4,
  },
  sendBtnText: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.background,
  },
});
