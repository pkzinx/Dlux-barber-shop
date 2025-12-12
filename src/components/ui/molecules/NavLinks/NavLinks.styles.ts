import styled, { css } from 'styled-components';
import { customMedia } from '../../../../utils/media/customMedia';
import { Link } from 'react-scroll';
import NextLink from 'next/link';

type ActiveProps = {
  $isActive?: boolean;
};

export const Wrapper = styled.nav`
  width: 100%;
  display: flex;
  align-items: center;
  height: 100%;
  position: relative;

  ${customMedia.greaterThan('medium')`
    width: auto;
  `}
`;

export const Line = styled.span`
  ${({ theme }) => css`
    height: 0.3rem;
    position: absolute;
    bottom: 0;
    left: 0;
    background: ${theme.colors.primary};
    border-radius: 0.3rem;
    transition: all 0.3s linear;
    box-shadow: 0 0 1rem ${theme.colors.primary};
  `}
`;

export const WrapperUl = styled.ul`
  display: flex;
  gap: 4rem;
`;

export const List = styled.li<ActiveProps>`
  ${({ theme, $isActive }) => css`
    list-style: none;
    color: ${$isActive ? theme.colors.primary : theme.colors.white};
    text-shadow: ${$isActive && `0 0 1rem ${theme.colors.primary}`};
  `}
`;

export const NavLink = styled(Link).attrs({
  spy: true,
  hashSpy: true,
  smooth: true,
  duration: 600,
  autoFocus: true,
  activeClass: 'active',
  offset: -100,
  isDynamic: true,
})`
  ${({ theme }) => css`
    text-decoration: none;
    font-size: ${theme.font.sizes.medium};
    transition: 0.3s linear;
    cursor: pointer;

    &:hover,
    &:focus {
      color: ${theme.colors.primary};
      text-shadow: 0 0 1rem ${theme.colors.primary};
      outline: none;
    }
  `}
`;

export const ExternalLink = styled(NextLink)`
  ${({ theme }) => css`
    text-decoration: none;
    font-size: ${theme.font.sizes.medium};
    transition: 0.3s linear;
    cursor: pointer;

    &:hover,
    &:focus {
      color: ${theme.colors.primary};
      text-shadow: 0 0 1rem ${theme.colors.primary};
      outline: none;
    }
  `}
`;
