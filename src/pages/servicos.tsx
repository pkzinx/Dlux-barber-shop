import Head from 'next/head';
import { GetServerSideProps } from 'next';
import styled from 'styled-components';
import { Header } from '@/components/ui/organisms/Header/Header';
import { Footer } from '@/components/ui/organisms/Footer/Footer';
import { ServiceBox } from '@/components/ui/molecules/ServiceBox/ServiceBox';
import { ScheduleModal } from '@/components/ui/molecules/ScheduleModal/ScheduleModal';
import contributors from '@/components/ui/organisms/SectionContributors/contributors.mock';
import { useState } from 'react';

type ServiceDTO = {
  id: number;
  title: string;
  price: string;
  duration_minutes: number;
  active: boolean;
};

type ServicePageProps = {
  services: ServiceDTO[];
  apiBase: string;
};

const Page = styled.div`
  background: #0b0b0f;
  min-height: 100vh;
  color: #ffffff;
`;

const Section = styled.main`
  max-width: 1200px;
  margin: 0 auto;
  padding: 6rem 1.5rem 4rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const HeaderBlock = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 2rem;
`;

const Subtitle = styled.p`
  margin: 0;
  color: #b3b3b3;
`;

const Grid = styled.div`
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
`;

const ServiceCard = styled.div`
  background: #11131a;
  border: 1px solid #1f2230;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  height: 100%;
  display: flex;
`;

const formatBRL = (value: number | string) => {
  const num = typeof value === 'string' ? Number(value) : value;
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(num || 0);
};

export default function ServicosPage({ services }: ServicePageProps) {
  const [selectedService, setSelectedService] = useState<string | undefined>();
  const [isOpen, setIsOpen] = useState(false);
  const barbers = contributors.map((c) => ({ name: c.name, src: c.src }));

  const onSchedule = (title: string) => {
    setSelectedService(title);
    setIsOpen(true);
  };

  return (
    <Page>
      <Head>
        <title>Serviços | Dlux Barbearia</title>
      </Head>
      <Header />
      <Section>
        <HeaderBlock>
          <Title>Todos os serviços</Title>
          <Subtitle>Valores e durações atualizados direto do painel.</Subtitle>
        </HeaderBlock>
        <Grid>
          {services.map((service) => (
            <ServiceCard key={service.id}>
              <ServiceBox
                infos={[
                  {
                    title: service.title,
                    price: formatBRL(service.price),
                    description: `Duração: ${service.duration_minutes} min`,
                  },
                ]}
                onSchedule={onSchedule}
              />
            </ServiceCard>
          ))}
        </Grid>
      </Section>
      <Footer />
      <ScheduleModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        barbers={barbers}
        serviceTitle={selectedService}
      />
    </Page>
  );
}

export const getServerSideProps: GetServerSideProps<ServicePageProps> = async ({ res }) => {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  
  // Set cache control headers for fresher content
  res.setHeader(
    'Cache-Control',
    'public, s-maxage=10, stale-while-revalidate=59'
  );

  try {
    const response = await fetch(`${apiBase}/api/services/public/`);
    const data = await response.json();
    return {
      props: {
        services: Array.isArray(data) ? data : data?.results || [],
        apiBase,
      },
    };
  } catch (err) {
    console.error('Falha ao carregar serviços', err);
    return {
      props: {
        services: [],
        apiBase,
      },
    };
  }
};

