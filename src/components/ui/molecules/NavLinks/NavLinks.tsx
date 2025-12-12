import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import MediaMatch from '../MediaMatch/MediaMatch';
import * as S from './NavLinks.styles';

export type NavLinkNames = {
  nav: string;
  link: string;
  offset?: number;
  href?: string;
};

export type NavLinksProps = {
  children: React.ReactNode;
  names: NavLinkNames[];
  paddingXLine: number;
};

export const NavLinks = ({ children, names, paddingXLine }: NavLinksProps) => {
  const [state, setState] = useState('home');
  const [dimensions, setDimensions] = useState({ width: 0, left: 0 });

  const refLink = useRef<HTMLLIElement>(null);
  const wrapperRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const updatePosition = () => {
      if (!refLink.current) return;
      const linkRect = refLink.current.getBoundingClientRect();
      const containerLeft = wrapperRef.current
        ? wrapperRef.current.getBoundingClientRect().left
        : 0;
      setDimensions({
        width: linkRect.width + paddingXLine * 2,
        left: linkRect.left - containerLeft - paddingXLine,
      });
    };

    updatePosition();

    window.addEventListener('load', updatePosition);
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, { passive: true });

    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition);
    };
  }, [state, paddingXLine]);

  return (
    <S.Wrapper ref={wrapperRef}>
      <MediaMatch $greaterThan="medium">
        <S.WrapperUl>
          {names.slice(0, names.length / 2).map(({ nav, link, offset, href }) => (
            <S.List
              key={link}
              $isActive={state === link}
              ref={state === link ? refLink : null}
            >
              {href ? (
                <Link href={href} passHref legacyBehavior>
                  <S.ExternalLink
                    aria-selected={state === link}
                    onClick={() => setState(link)}
                  >
                    {nav}
                  </S.ExternalLink>
                </Link>
              ) : (
                <S.NavLink
                  to={link}
                  aria-selected={state === link}
                  onSetActive={setState}
                  onClick={() => setState(link)}
                  offset={offset}
                >
                  {nav}
                </S.NavLink>
              )}
            </S.List>
          ))}
        </S.WrapperUl>
      </MediaMatch>

      {children}

      <MediaMatch $greaterThan="medium">
        <S.WrapperUl>
          {names.slice(names.length / 2, names.length).map(({ nav, link, offset, href }) => (
            <S.List
              key={link}
              $isActive={state === link}
              ref={state === link ? refLink : null}
            >
              {href ? (
                <Link href={href} passHref legacyBehavior>
                  <S.ExternalLink
                    aria-selected={state === link}
                    onClick={() => setState(link)}
                  >
                    {nav}
                  </S.ExternalLink>
                </Link>
              ) : (
                <S.NavLink
                  to={link}
                  aria-selected={state === link}
                  onSetActive={setState}
                  onClick={() => setState(link)}
                  offset={offset}
                >
                  {nav}
                </S.NavLink>
              )}
            </S.List>
          ))}
        </S.WrapperUl>

        <S.Line
          style={{
            width: `${dimensions.width}px`,
            transform: `translateX(${dimensions.left}px)`,
          }}
          aria-label="Line"
        />
      </MediaMatch>
    </S.Wrapper>
  );
};
