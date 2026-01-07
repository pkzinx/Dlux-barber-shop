import React, { useState } from 'react';
import * as S from './ScheduleModal.styles';

import { Button } from '../../atoms/Button/Button';
import { addAppointment } from '@/utils/appointmentsStorage';
import { registerAppointmentPush } from '@/utils/push';
import { InputGroup } from '../InputGroup/InputGroup';
import { SelectGroup } from '../SelectGroup/SelectGroup';
import { ModalForm } from '../ModalForm/ModalForm';

export type Barber = {
  name: string;
  src: string;
};

export type ScheduleModalProps = {
  isOpen: boolean;
  onClose: () => void;
  barbers: Barber[];
  serviceTitle?: string;
};

export const ScheduleModal = ({ isOpen, onClose, barbers, serviceTitle }: ScheduleModalProps) => {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [barberName, setBarberName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState<'success' | 'error'>('success');
  const [timeOptions, setTimeOptions] = useState<string[]>([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [lastAppointment, setLastAppointment] = useState<{
    barber: string;
    service: string;
    date: string;
    time: string;
    startIso: string;
    endIso: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      // Monta datas
      const startDatetime = `${date}T${time}:00`;
      // Duração baseada no serviço selecionado
      const durationMinutes = serviceDurationMinutes;
      const start = new Date(startDatetime);
      const end = new Date(start.getTime() + durationMinutes * 60000);
      const pad = (n: number) => String(n).padStart(2, '0');
      const endDatetime = `${end.getFullYear()}-${pad(end.getMonth() + 1)}-${pad(end.getDate())}T${pad(end.getHours())}:${pad(end.getMinutes())}:00`;

      // Envia via API do Next.js (proxy) para o backend
      const resp = await fetch('/api/appointments/public/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          barberName,
          clientName: name,
          clientPhone: phone,
          serviceTitle,
          startDatetime,
          endDatetime,
          notes: `Agendado via site${serviceTitle ? ' - ' + serviceTitle : ''}`,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data?.detail || 'Falha ao agendar');
      
      const apptDetails = {
        barber: barberName,
        service: serviceTitle || 'Serviço',
        date: date.split('-').reverse().join('/'),
        time,
        startIso: startDatetime.replace(/[-:]/g, ''),
        endIso: endDatetime.replace(/[-:]/g, ''),
      };
      setLastAppointment(apptDetails);

      // Persistir agendamento localmente (sem exigir login)
      try {
        addAppointment({
          id: data?.id ? String(data.id) : undefined,
          serviceTitle: serviceTitle || 'Serviço',
          barberName,
          clientName: name,
          startDatetime,
          endDatetime,
        });
      } catch (_) {
        // Ignorar falhas de armazenamento local
      }
      // Solicitar permissão e registrar token de push para este agendamento
      try {
        if (data?.id) {
          await registerAppointmentPush(String(data.id));
        }
      } catch (_) {
        // Ignorar falhas de registro de push
      }
      // Sucesso: fecha modal de agendamento e abre feedback de sucesso
      onClose();
      setFeedbackStatus('success');
      setFeedbackOpen(true);
      // Opcional: limpar campos
      setName(''); setPhone(''); setDate(''); setTime(''); setBarberName('');
    } catch (err) {
      setFeedbackStatus('error');
      setFeedbackOpen(true);
    } finally {
      setSubmitting(false);
    }
  };

  // Utilidades para datas e horários
  const toYMD = (d: Date) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  const formatDM = (d: Date) => d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });

  const today = new Date();
  const todayYMD = toYMD(today);

  const dateOptions = React.useMemo(() => {
    // Gera próximos 30 dias, removendo domingos e feriados (seg a sáb)
    const options: { label: string; value: string }[] = [];
    const start = new Date();

    const isSunday = (d: Date) => d.getDay() === 0;

    const isBrazilHoliday = (d: Date) => {
      // Feriados nacionais fixos (sem considerar móveis) – formato MM-DD
      const fixed: Set<string> = new Set([
        '01-01', // Confraternização Universal
        '04-21', // Tiradentes
        '05-01', // Dia do Trabalho
        '09-07', // Independência do Brasil
        '10-12', // Nossa Senhora Aparecida
        '11-02', // Finados
        '11-15', // Proclamação da República
        '12-25', // Natal
      ]);
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const key = `${mm}-${dd}`;
      // Remover feriados que caem de segunda(1) a sábado(6)
      const weekday = d.getDay();
      return weekday >= 1 && weekday <= 6 && fixed.has(key);
    };

    for (let i = 0; i < 30; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      if (isSunday(d)) continue;
      if (isBrazilHoliday(d)) continue;
      options.push({ label: formatDM(d), value: toYMD(d) });
    }
    return options;
  }, []);

  const generateSlots = () => {
    const slots: string[] = [];
    for (let h = 8; h <= 17; h++) {
      for (const m of [0, 20, 40]) {
        const hh = String(h).padStart(2, '0');
        const mm = String(m).padStart(2, '0');
        const t = `${hh}:${mm}`;
        // Limitar até 17:40
        if (h === 17 && m > 40) continue;
        slots.push(t);
      }
    }
    return slots;
  };

  const roundUpTo20 = (d: Date) => {
    let h = d.getHours();
    let m = d.getMinutes();
    const bucket = Math.ceil(m / 20) * 20;
    if (bucket === 60) {
      h = h + 1;
      m = 0;
    } else {
      m = bucket;
    }
    const hh = String(h).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    return `${hh}:${mm}`;
  };

  const allSlots = React.useMemo(() => generateSlots(), []);

  const serviceDurationMinutes = React.useMemo(() => {
    const normalized = (serviceTitle || '').toLowerCase().trim();
    if (normalized.includes('pezinho perfil acabamento')) return 5;
    if (normalized.includes('barba') && normalized.includes('cabelo')) return 60;
    if (normalized.includes('barba')) return 30;
    if (normalized.includes('cabelo')) return 40;
    return 40; // padrão
  }, [serviceTitle]);

  const abortControllerRef = React.useRef<AbortController | null>(null);

  const fetchAvailableSlots = async (selectedDate: string, selectedBarberName: string) => {
    if (!selectedDate || !selectedBarberName) {
      setTimeOptions([]);
      return;
    }

    // Cancelar requisição anterior se houver
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Evitar fetch se os parâmetros não mudaram ou se faltar dados
    // Mas se houver um controller novo, devemos permitir a busca se for diferente
    // A verificação de igualdade deve ser cuidadosa com aborts
    
    try {
      setLoadingSlots(true);
      const params = new URLSearchParams({
        date: selectedDate,
        barberName: selectedBarberName.trim(),
        durationMinutes: String(serviceDurationMinutes),
      });
      
      const r = await fetch(`/api/appointments/available-slots/?${params.toString()}`, {
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      
      const data = await r.json();
      
      if (!r.ok) {
        console.error('Erro ao buscar horários disponíveis:', data);
        setTimeOptions([]);
      } else {
        const slots: string[] = Array.isArray(data?.slots) ? data.slots : [];
        setTimeOptions(slots);
        if (time && !slots.includes(time)) setTime('');
      }
    } catch (e: any) {
      if (e.name === 'AbortError') {
        // Requisição cancelada intencionalmente, ignorar
        return;
      }
      console.error('Falha na requisição de disponibilidade:', e);
      setTimeOptions([]);
    } finally {
      // Só remover loading se este for o controller atual (não foi abortado por outro)
      if (abortControllerRef.current === controller) {
        setLoadingSlots(false);
        abortControllerRef.current = null;
      }
    }
  };

  // Se o horário atual ficar inválido após trocar dependências, limpar tempo
  React.useEffect(() => {
    if (time && !timeOptions.includes(time)) setTime('');
  }, [timeOptions, time]);

  // Atualiza horários ao trocar serviço (pois muda a duração)
  React.useEffect(() => {
    if (date && barberName) {
        // Debounce simples para evitar múltiplas chamadas rápidas
        const t = setTimeout(() => fetchAvailableSlots(date, barberName), 50);
        return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serviceDurationMinutes]);

  return (
    <>
      <S.Background aria-hidden={isOpen} aria-label="Overlay Modal" $isOpen={isOpen} />
      <S.Modal $isOpen={isOpen} aria-label="Modal">
        <S.Title>Agendar Serviço {serviceTitle ? `- ${serviceTitle}` : ''}</S.Title>
        <S.Form onSubmit={handleSubmit}>
          {/* Seleção de barbeiros logo abaixo do título */}
          <S.FullRow>
            <S.BarberGrid>
              {barbers.map(({ name: bName, src }) => (
                <S.BarberCard key={bName} $selected={barberName === bName}>
                  <input
                    type="radio"
                    name="barber"
                    value={bName}
                    checked={barberName === bName}
                    onChange={() => {
                      setBarberName(bName);
                      if (date) fetchAvailableSlots(date, bName);
                    }}
                    style={{ display: 'none' }}
                  />
                  <S.BarberAvatar src={src} alt={`Foto do barbeiro ${bName}`} />
                  <span>{bName}</span>
                </S.BarberCard>
              ))}
            </S.BarberGrid>
          </S.FullRow>

          <S.FullRow>
            <InputGroup
              label="Nome"
              labelFor="nome"
              required
              type="text"
              value={name}
              placeholder="Ex: João Silva"
              onChange={(e: any) => setName(e.target.value)}
              marginBottom
            />
          </S.FullRow>

          <InputGroup
            label="Telefone"
            labelFor="telefone"
            required
            type="text"
            value={phone}
            placeholder="Ex: (11) 99999-9999"
            onChange={(e: any) => setPhone(e.target.value)}
          />

          <S.FieldInline>
            <SelectGroup
              label="Data"
              labelFor="data"
              required
              placeholder="Selecione a data"
              value={date}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                const v = e.target.value;
                setDate(v);
                if (barberName) fetchAvailableSlots(v, barberName);
              }}
            >
              {dateOptions.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </SelectGroup>
            <SelectGroup
              label="Horário"
              labelFor="horario"
              required
              placeholder={loadingSlots ? 'Carregando...' : (timeOptions.length ? 'Selecione o horário' : (date && barberName ? 'Sem horários disponíveis' : 'Selecione data e barbeiro'))}
              value={time}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTime(e.target.value)}
              disabled={!date || !barberName || loadingSlots || timeOptions.length === 0}
            >
              {timeOptions.map(t => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </SelectGroup>
          </S.FieldInline>

          {/* Seleção de barbeiros movida para cima; campos de data/hora permanecem aqui */}

          <S.Actions>
            <Button as="button" type="button" onClick={onClose}>
              Cancelar
            </Button>
            <Button as="button" type="submit" disabled={!barberName || !name || !phone || !date || !time || submitting}>
              {submitting ? 'Agendando...' : 'Agendar'}
            </Button>
          </S.Actions>
        </S.Form>
      </S.Modal>
      {feedbackStatus === 'error' ? (
        <ModalForm
          status="error"
          isOpen={feedbackOpen}
          onClick={() => setFeedbackOpen(false)}
        />
      ) : (
        <>
          <S.Background aria-hidden={feedbackOpen} aria-label="Overlay Modal" $isOpen={feedbackOpen} />
          <S.Modal $isOpen={feedbackOpen} aria-label="Modal Sucesso" style={{ textAlign: 'center' }}>
             <img src="/assets/svg/icon-success.svg" alt="Sucesso" style={{ width: '8rem', height: '8rem', marginBottom: '1rem' }} />
             <S.Title>Agendamento Realizado!</S.Title>
             {lastAppointment && (
               <div style={{ color: '#fff', fontSize: '1.6rem', margin: '2rem 0', lineHeight: '1.5' }}>
                 <p><strong>Serviço:</strong> {lastAppointment.service}</p>
                 <p><strong>Barbeiro:</strong> {lastAppointment.barber}</p>
                 <p><strong>Data:</strong> {lastAppointment.date} às {lastAppointment.time}</p>
               </div>
             )}
             <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', maxWidth: '300px' }}>
               {lastAppointment && (
                 <>
                   <Button
                     as="a"
                     href={`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent('Dlux: ' + lastAppointment.service)}&dates=${lastAppointment.startIso}/${lastAppointment.endIso}&details=${encodeURIComponent('Barbeiro: ' + lastAppointment.barber)}&location=Dlux`}
                     target="_blank"
                     rel="noopener noreferrer"
                     style={{ textDecoration: 'none' }}
                   >
                     Adicionar ao Google Agenda
                   </Button>
                   <Button
                     as="a"
                     href={`https://wa.me/?text=${encodeURIComponent(`Olá, confirmo meu agendamento na Dlux com ${lastAppointment.barber} para ${lastAppointment.service} dia ${lastAppointment.date} às ${lastAppointment.time}.`)}`}
                     target="_blank"
                     rel="noopener noreferrer"
                     style={{ textDecoration: 'none', backgroundColor: '#25D366', borderColor: '#25D366' }}
                   >
                     Enviar confirmação no WhatsApp
                   </Button>
                 </>
               )}
               <Button as="button" type="button" onClick={() => {
                  setFeedbackOpen(false);
                  try {
                    if (typeof window !== 'undefined') window.location.reload();
                  } catch (_) {}
                }} $buttonStyle="secondary">
                  Fechar
                </Button>
             </div>
          </S.Modal>
        </>
      )}
    </>
  );
};