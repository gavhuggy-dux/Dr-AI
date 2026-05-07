import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator, Alert,
} from 'react-native';
import { colors, borderRadius } from '../theme';
import apiClient from '../api/client';

const CREDIT_COST_PER_MINUTE = 2;

export default function BookAppointmentScreen({ navigation }) {
  const [mainComplaint, setMainComplaint] = useState('');
  const [duration, setDuration] = useState(15);
  const [loading, setLoading] = useState(false);
  const [creditBalance, setCreditBalance] = useState(null);

  React.useEffect(() => {
    apiClient.getCreditBalance()
      .then(d => setCreditBalance(d.balance ?? 0))
      .catch(() => {});
  }, []);

  const creditCost = duration * CREDIT_COST_PER_MINUTE;

  async function handleBook() {
    if (!mainComplaint.trim()) {
      Alert.alert('Error', 'Please describe your main complaint');
      return;
    }
    if (creditBalance !== null && creditCost > creditBalance) {
      Alert.alert('Insufficient Credits', `You need ${creditCost} credits but only have ${creditBalance}. Please top up.`);
      return;
    }

    setLoading(true);
    try {
      const appointment = await apiClient.bookAppointment({
        main_complaint: mainComplaint.trim(),
        duration_minutes: duration,
      });
      Alert.alert(
        'Appointment Booked',
        'Your consultation has been scheduled.',
        [
          {
            text: 'Start Now',
            onPress: async () => {
              try {
                await apiClient.startAppointment(appointment.id);
                navigation.replace('Consultation', { appointmentId: appointment.id });
              } catch (e) {
                navigation.goBack();
              }
            },
          },
          { text: 'OK', onPress: () => navigation.goBack() },
        ]
      );
    } catch (e) {
      Alert.alert('Booking Failed', e.message);
    } finally {
      setLoading(false);
    }
  }

  const durations = [15, 30, 45, 60];

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Book Appointment</Text>
          <Text style={styles.subtitle}>Describe your health concern</Text>
        </View>

        {/* Credit balance */}
        {creditBalance !== null && (
          <View style={styles.balanceBar}>
            <Text style={styles.balanceLabel}>Your Balance</Text>
            <Text style={styles.balanceAmount}>{creditBalance} credits</Text>
          </View>
        )}

        <Text style={styles.label}>Main Complaint</Text>
        <TextInput
          style={styles.complaintInput}
          value={mainComplaint}
          onChangeText={setMainComplaint}
          placeholder="Describe your symptoms or health concern..."
          placeholderTextColor={colors.textSecondary}
          multiline
          numberOfLines={4}
          textAlignVertical="top"
        />

        <Text style={styles.label}>Duration</Text>
        <View style={styles.durationRow}>
          {durations.map(d => (
            <TouchableOpacity
              key={d}
              style={[
                styles.durationBtn,
                duration === d && styles.durationBtnActive,
              ]}
              onPress={() => setDuration(d)}
            >
              <Text
                style={[
                  styles.durationBtnText,
                  duration === d && styles.durationBtnTextActive,
                ]}
              >
                {d} min
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Cost Summary */}
        <View style={styles.costCard}>
          <View style={styles.costRow}>
            <Text style={styles.costLabel}>Duration</Text>
            <Text style={styles.costValue}>{duration} minutes</Text>
          </View>
          <View style={styles.costRow}>
            <Text style={styles.costLabel}>Rate</Text>
            <Text style={styles.costValue}>{CREDIT_COST_PER_MINUTE} credits/min</Text>
          </View>
          <View style={[styles.costRow, styles.costTotalRow]}>
            <Text style={styles.costTotalLabel}>Total Cost</Text>
            <Text style={styles.costTotalValue}>{creditCost} credits</Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.bookButton, loading && styles.bookButtonDisabled]}
          onPress={handleBook}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color={colors.background} />
          ) : (
            <Text style={styles.bookButtonText}>Confirm Booking</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.white,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  balanceBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    padding: 14,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: colors.accent + '30',
  },
  balanceLabel: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  balanceAmount: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.accent,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.text,
    marginBottom: 8,
    marginTop: 8,
  },
  complaintInput: {
    backgroundColor: colors.inputBg,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    borderRadius: borderRadius.md,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    color: colors.white,
    minHeight: 120,
  },
  durationRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 20,
  },
  durationBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.card,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  durationBtnActive: {
    borderColor: colors.accent,
    backgroundColor: colors.accent + '15',
  },
  durationBtnText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  durationBtnTextActive: {
    color: colors.accent,
  },
  costCard: {
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.cardBorder,
    marginBottom: 24,
  },
  costRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  costLabel: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  costValue: {
    fontSize: 14,
    color: colors.text,
    fontWeight: '500',
  },
  costTotalRow: {
    borderTopWidth: 1,
    borderTopColor: colors.cardBorder,
    marginTop: 6,
    paddingTop: 10,
  },
  costTotalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  costTotalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.accent,
  },
  bookButton: {
    backgroundColor: colors.accent,
    borderRadius: borderRadius.md,
    paddingVertical: 16,
    alignItems: 'center',
  },
  bookButtonDisabled: {
    opacity: 0.6,
  },
  bookButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.background,
  },
});
