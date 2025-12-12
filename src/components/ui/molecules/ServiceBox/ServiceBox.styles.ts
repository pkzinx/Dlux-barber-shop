import styled, { css } from 'styled-components';
import media from 'styled-media-query';

export const Wrapper = styled.section`
  ${({ theme }) => css`
    display: flex;
    width: 100%;
    height: 100%;
    flex-direction: column;
    gap: ${theme.spacings.large};
    padding: ${theme.spacings.large} calc(${theme.spacings.large} / 2);
    background: #0f111a;
    border: 1px solid #1f2230;
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.35);
    border-radius: 1rem;

    ${media.greaterThan('medium')`
      gap: ${theme.spacings.huge};
      padding: ${theme.spacings.huge} calc(${theme.spacings.large} / 2);
      height: auto;
    `}
  `}
`;

export const ContentInfos = styled.div`
  ${({ theme }) => css`
    display: flex;
    flex-direction: column;
    gap: calc(${theme.spacings.large} / 2);

    ${media.greaterThan('medium')`
      gap: 3rem;
    `}
  `}
`;

export const Content = styled.div`
  ${({ theme }) => css`
    color: ${theme.colors.white};
  `}
`;

export const InfoPrimary = styled.div`
  ${({ theme }) => css`
    display: flex;
    justify-content: space-between;
    font-size: ${theme.font.sizes.small};
  `}
`;

export const Title = styled.h5`
  ${({ theme }) => css`
    font-size: ${theme.font.sizes.small};
    font-weight: 400;
  `}
`;

export const Price = styled.p`
  ${({ theme }) => css`
    color: ${theme.colors.primary};
  `}
`;

export const Description = styled.div`
  ${({ theme }) => css`
    font-size: ${theme.font.sizes.xsmall};
    margin-top: 0.5rem;
  `}
`;

export const ScheduleButton = styled.button`
  ${({ theme }) => css`
    display: block;
    margin: ${theme.spacings.xxsmall} auto 0;
    padding: 0.9rem 1.8rem;
    border-radius: 0.6rem;
    border: 0;
    cursor: pointer;
    color: ${theme.colors.white};
    background: ${theme.colors.primary};
    font-size: ${theme.font.sizes.small};
    font-weight: 500;
    min-width: 12rem;

    &:hover {
      filter: brightness(1.05);
    }

    ${media.greaterThan('medium')`
      font-size: ${theme.font.sizes.medium};
    `}
  `}
`;
