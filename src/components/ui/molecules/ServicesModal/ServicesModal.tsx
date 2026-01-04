import * as S from './ServicesModal.styles';
import { Button } from '../../atoms/Button/Button';

export type ServiceItem = {
  title: string;
  duration: string;
  price: string;
  description?: string;
};

export type ServicesModalProps = {
  isOpen: boolean;
  onClose: () => void;
  services: ServiceItem[];
  onSchedule: (serviceTitle: string) => void;
};

export const ServicesModal = ({ isOpen, onClose, services, onSchedule }: ServicesModalProps) => {
  return (
    <>
      <S.Background aria-hidden={isOpen} aria-label="Overlay Modal" $isOpen={isOpen} />
      <S.Modal aria-label="Modal Serviços" $isOpen={isOpen}>
        <S.Header>
          <S.Title>Serviços e Valores</S.Title>
          <Button as="button" type="button" onClick={onClose}>
            Fechar
          </Button>
        </S.Header>

        <S.Content>
          {services.map((item) => (
            <S.Card key={`service-${item.title}`}>
              <S.CardHeader>
                <S.ServiceName>{item.title}</S.ServiceName>
                <S.Price>{item.price}</S.Price>
              </S.CardHeader>
              <S.Meta>Duração: {item.duration}</S.Meta>
              <S.CardActions>
                <Button
                  as="button"
                  type="button"
                  onClick={() => {
                    onSchedule(item.title);
                    onClose();
                  }}
                >
                  Agendar
                </Button>
              </S.CardActions>
            </S.Card>
          ))}
        </S.Content>

        <S.Footer>
          <Button as="button" type="button" $buttonStyle="secondary" onClick={onClose}>
            Entendi
          </Button>
        </S.Footer>
      </S.Modal>
    </>
  );
};
