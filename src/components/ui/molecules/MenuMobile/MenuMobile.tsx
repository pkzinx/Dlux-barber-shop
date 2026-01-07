import * as S from './MenuMobile.styles';

import { useEffect, useMemo, useState } from 'react';
import { getActiveAppointments, removeAppointment, clearExpired, onStorageChange, StoredAppointment } from '@/utils/appointmentsStorage';
import * as Styles from './MenuMobile.styles';

export type MenuMobileProps = {
  $isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
};

export const MenuMobile = ({ $isOpen, setIsOpen }: MenuMobileProps) => {
  const [isActive, setIsActive] = useState('home');
  const [appointments, setAppointments] = useState<StoredAppointment[]>([]);

  // Carregar agendamentos ativos ao abrir o menu e manter atualizado
  useEffect(() => {
    // Limpar expirados e carregar
    clearExpired();
    setAppointments(getActiveAppointments());

    // Ouvir mudanças no storage (caso agende em outra aba)
    const off = onStorageChange((items) => setAppointments(items));

    // Atualizar in-place a cada minuto para expirar automaticamente
    const interval = setInterval(() => {
      clearExpired();
      setAppointments(getActiveAppointments());
    }, 60 * 1000);

    return () => {
      off();
      clearInterval(interval);
    };
  }, []);

  const hasAppointments = appointments.length > 0;
  const headerText = useMemo(
    () => (hasAppointments ? `Seus agendamentos (${appointments.length})` : 'Nenhum agendamento ativo'),
    [hasAppointments, appointments.length]
  );

  return (
    <S.Wrapper aria-hidden={!$isOpen} aria-label="Menu Full" $isOpen={$isOpen}>
      <S.WrapperList>
        <Styles.NoticeSection>
          <Styles.NoticeHeader>
            <span>{headerText}</span>
            <Styles.CloseButton
              aria-label="Fechar menu"
              title="Fechar"
              onClick={() => setIsOpen(false)}
            >
              ×
            </Styles.CloseButton>
          </Styles.NoticeHeader>
          {hasAppointments && (
            <Styles.NoticeList>
              {appointments.map((a) => {
                const start = new Date(a.startDatetime);
                const pad = (n: number) => String(n).padStart(2, '0');
                const time = `${pad(start.getHours())}:${pad(start.getMinutes())}`;
                return (
                  <Styles.NoticeItem key={a.id}>
                    <div>
                      <strong>{time}</strong> — {a.serviceTitle}
                      {a.barberName ? ` • ${a.barberName}` : ''}
                    </div>
                    <Styles.NoticeCancel
                      aria-label={`Cancelar agendamento ${a.serviceTitle} ${time}`}
                      onClick={async () => {
                        try {
                          if (a.id) {
                            const resp = await fetch('/api/appointments/cancel/', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ id: a.id }),
                            });
                            const data = await resp.json();
                            if (!resp.ok) {
                              console.error('Falha ao cancelar no painel:', data);
                              alert('Não foi possível cancelar no painel. Tente novamente.');
                              return;
                            }
                          }
                          // Remover localmente após sucesso no painel
                          removeAppointment(a.id);
                          setAppointments(getActiveAppointments());
                        } catch (err) {
                          console.error('Erro de cancelamento:', err);
                          alert('Erro ao cancelar. Verifique sua conexão e tente novamente.');
                        }
                      }}
                    >
                      Cancelar
                    </Styles.NoticeCancel>
                  </Styles.NoticeItem>
                );
              })}
            </Styles.NoticeList>
          )}
        </Styles.NoticeSection>
        <S.List $isActive={isActive === 'home'}>
          <S.MenuLink
            to="home"
            aria-label="Home"
            onSetActive={setIsActive}
            onClick={() => setIsOpen(!$isOpen)}
          >
            Home
          </S.MenuLink>
        </S.List>
        <S.List $isActive={isActive === 'sobre'}>
          <S.MenuLink
            to="sobre"
            aria-label="Sobre"
            onSetActive={setIsActive}
            onClick={() => setIsOpen(!$isOpen)}
          >
            Sobre
          </S.MenuLink>
        </S.List>
        <S.List $isActive={isActive === 'servicos'}>
          <S.MenuLink
            to="servicos"
            aria-label="Serviços"
            onSetActive={setIsActive}
            onClick={() => setIsOpen(!$isOpen)}
          >
            Serviços
          </S.MenuLink>
        </S.List>
        <S.List $isActive={isActive === 'equipe'}>
          <S.MenuLink
            to="equipe"
            aria-label="Equipe"
            onSetActive={setIsActive}
            onClick={() => setIsOpen(!$isOpen)}
          >
            Equipe
          </S.MenuLink>
        </S.List>
        <S.List $isActive={isActive === 'opiniao'}>
          <S.MenuLink
            to="avaliacao"
            aria-label="Opinião"
            onSetActive={setIsActive}
            onClick={() => setIsOpen(!$isOpen)}
          >
            Avaliações
          </S.MenuLink>
        </S.List>
        <S.List $isActive={isActive === 'feedback'}>
          <S.MenuLink
            to="feedback"
            aria-label="FeedBack"
            onSetActive={setIsActive}
            onClick={() => setIsOpen(!$isOpen)}
          >
            FeedBack
          </S.MenuLink>
        </S.List>
      </S.WrapperList>
    </S.Wrapper>
  );
};
