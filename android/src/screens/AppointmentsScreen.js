import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList,
  RefreshControl, ActivityIndicator,
} from 'react-native';
import { colors, borderRadius } from '../theme';
import apiClient from '../api/client';

export default function AppointmentsScreen({ navigation }) {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAppointments();
  }, []);

  async function loadAppointments() {
    try {
      const data = await apiClient.getAppointments();
      if (Array.isArray(data)) {
        setAppointments(data);
      }
    } catch (e) {
      console.error('Failed to load appointments:', e);
    } finally {
      setLoading(false);
    }
  }

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadAppointments();
    setRefreshing(false);
  }, []);

  function getStatusStyle(status) {
    switch (status?.toLowerCase()) {
      case 'scheduled':
      case 'pending':
        return { bg: '#ffd43b20', text: '#ffd43b' };
      case 'in_progress':
      case 'active':
        return { bg: '#5ccfe620', text: colors.accent };
      case 'completed':
      case 'done':
        return { bg: '#51cf6620', text: colors.success };
      case 'cancelled':
        return { bg: '#ff6b6b20', text: colors.error };
      default:
        return { bg: colors.cardBorder, text: colors.textSecondary };
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  }

  function handleAppointmentPress(item) {
    if (item.status === 'in_progress' || item.status === 'active') {
      navigation.navigate('Consultation', { appointmentId: item.id });
    }
  }

  function renderAppointment({ item }) {
    const statusStyle = getStatusStyle(item.status);
    const canStart = item.status === 'scheduled' || item.status === 'pending';

    return (
      <TouchableOpacity
        style={styles.appointmentCard}
        onPress={() => handleAppointmentPress(item)}
        disabled={!canStart && item.status !== 'in_progress'}
      >
        <View style={styles.apptHeader}>
          <Text style={styles.apptTitle}>{item.main_complaint || 'Consultation'}</Text>
          <View style={[styles.statusBadge, { backgroundColor: statusStyle.bg }]}>
            <Text style={[styles.statusText, { color: statusStyle.text }]}>
              {item.status || 'scheduled'}
            </Text>
          </View>
        </View>
        <Text style={styles.apptDate}>{formatDate(item.scheduled_at || item.created_at)}</Text>
        {item.duration_minutes && (
          <Text style={styles.apptDuration}>Duration: {item.duration_minutes} min</Text>
        )}
        {canStart && (
          <TouchableOpacity
            style={styles.startBtn}
            onPress={async () => {
              try {
                await apiClient.startAppointment(item.id);
                navigation.navigate('Consultation', { appointmentId: item.id });
              } catch (e) {
                Alert.alert('Error', e.message);
              }
            }}
          >
            <Text style={styles.startBtnText}>Start Consultation</Text>
          </TouchableOpacity>
        )}
      </TouchableOpacity>
    );
  }

  if (loading) {
    return (
      <View style={styles.centerContent}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>My Appointments</Text>
        <Text style={styles.subtitle}>{appointments.length} appointment(s)</Text>
      </View>

      <FlatList
        data={appointments}
        renderItem={renderAppointment}
        keyExtractor={(item, index) => String(item.id || index)}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={colors.accent}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>📅</Text>
            <Text style={styles.emptyText}>No appointments yet</Text>
            <Text style={styles.emptySubtext}>Book your first consultation</Text>
          </View>
        }
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('BookAppointment')}
      >
        <Text style={styles.fabText}>+ Book New</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    padding: 20,
    paddingBottom: 10,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.white,
  },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 2,
  },
  centerContent: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  list: {
    padding: 20,
    paddingTop: 10,
    paddingBottom: 80,
  },
  appointmentCard: {
    backgroundColor: colors.card,
    borderRadius: borderRadius.md,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.cardBorder,
  },
  apptHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  apptTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.white,
    flex: 1,
    marginRight: 8,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  apptDate: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 6,
  },
  apptDuration: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  startBtn: {
    backgroundColor: colors.accent,
    borderRadius: borderRadius.sm,
    paddingVertical: 10,
    alignItems: 'center',
    marginTop: 12,
  },
  startBtnText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.background,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    color: colors.text,
    fontWeight: '600',
  },
  emptySubtext: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 4,
  },
  fab: {
    position: 'absolute',
    bottom: 24,
    right: 20,
    backgroundColor: colors.accent,
    borderRadius: 28,
    paddingVertical: 14,
    paddingHorizontal: 24,
    shadowColor: colors.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  fabText: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.background,
  },
});
