import Link from 'next/link';
import MediaMatch from '../../molecules/MediaMatch/MediaMatch';
import { useEffect, useState } from 'react';

import { Background } from '../../atoms/Background/Background';
import { Button } from '../../atoms/Button/Button';
import { Heading } from '../../molecules/Heading/Heading';
import {
  ServiceBox,
  ServiceBoxProps,
} from '../../molecules/ServiceBox/ServiceBox';
import { Slider, SliderSettings } from '../../molecules/Slider/Slider';
import { ScheduleModal } from '../../molecules/ScheduleModal/ScheduleModal';
import contributors from '../SectionContributors/contributors.mock';
import { ServicesModal, ServiceItem } from '../../molecules/ServicesModal/ServicesModal';

import * as S from './MainServices.styles';

export type MainServicesProps = {
  items: ServiceBoxProps[];
};

const settings: SliderSettings = {
  slidesToShow: 2,
  arrows: false,
  infinite: false,
  speed: 500,
  responsive: [
    {
      breakpoint: 600,
      settings: {
        slidesToShow: 1.05,
        arrows: false,
        infinite: false,
        speed: 500,
      },
    },
  ],
};

export const MainServices = ({ items }: MainServicesProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedService, setSelectedService] = useState<string | undefined>();
  const [isServicesOpen, setIsServicesOpen] = useState(false);
  const [servicesList, setServicesList] = useState<ServiceItem[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);

  // Exibir os 5 barbeiros da seção de equipe com nomes e fotos
  const barbers = contributors.map((c) => ({ name: c.name, src: c.src }));

  const openSchedule = (serviceTitle: string) => {
    setSelectedService(serviceTitle);
    setIsOpen(true);
  };

  const fetchServices = async () => {
    setLoadingServices(true);
    try {
      const url = `/api/services/public`;
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        cache: 'no-store',
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      const list = Array.isArray(data) ? data : data?.results || [];
      const mapped: ServiceItem[] = list.map((s: any) => ({
        title: s.title,
        duration: s.duration_minutes ? `${s.duration_minutes} min` : '',
        price: s.price
          ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(s.price))
          : '',
      }));
      setServicesList(mapped);
    } catch (err) {
      console.error('Erro ao buscar serviços da API:', err);
      // fallback: usar serviços atuais do slider se falhar
      const fallback: ServiceItem[] = items.flatMap(({ infos }) =>
        infos.map(info => ({
          title: info.title,
          duration: '',
          price: info.price,
        }))
      );
      setServicesList(fallback);
    } finally {
      setLoadingServices(false);
    }
  };

  // Buscar serviços ao montar o componente
  useEffect(() => {
    fetchServices();
  }, [items]);

  // Buscar serviços sempre que o modal abrir para garantir dados atualizados
  useEffect(() => {
    if (isServicesOpen) {
      fetchServices();
    }
  }, [isServicesOpen]);

  return (
    <S.Wrapper>
      <Background src="/assets/img/slide-4.jpg">
        <Heading
          title="Pronto para Cortar"
          subtitle="Principais Serviços"
          lineBottom
        />

        <MediaMatch $greaterThan="large">
          <S.WrapperServicesBox>
            {items.map(({ infos }, index) => (
              <ServiceBox key={`Service - ${index}`} infos={infos} onSchedule={openSchedule} />
            ))}
          </S.WrapperServicesBox>
        </MediaMatch>

        <MediaMatch $lessThan="large">
          <Slider settings={settings}>
            {items.map(({ infos }, index) => (
              <ServiceBox
                key={`Service in the slider - ${index}`}
                infos={infos}
                onSchedule={openSchedule}
              />
            ))}
          </Slider>
          <S.SwipeHint>
            Rolar para ver os outros serviços
            <S.SwipeVisual aria-hidden="true">
              <svg width="12" height="12" viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
                <polyline points="0,0 6,6 0,12" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
              <svg width="12" height="12" viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
                <polyline points="0,0 6,6 0,12" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            </S.SwipeVisual>
          </S.SwipeHint>
        </MediaMatch>

        <S.BottomAction>
          <Button as="button" type="button" $buttonStyle="secondary" onClick={() => setIsServicesOpen(true)}>
            Ver todos os serviços
          </Button>
        </S.BottomAction>

      <ScheduleModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        barbers={barbers}
        serviceTitle={selectedService}
      />

      <ServicesModal
        isOpen={isServicesOpen}
        onClose={() => setIsServicesOpen(false)}
        services={servicesList}
        onSchedule={openSchedule}
      />

      </Background>
    </S.Wrapper>
  );
};
